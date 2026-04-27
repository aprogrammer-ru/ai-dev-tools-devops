using System.Data;
using Dapper;
using Npgsql;
using StackExchange.Redis;
using Microsoft.Extensions.DependencyInjection;

var builder = WebApplication.CreateBuilder(args);

var settings = AppSettings.FromConfiguration(builder.Configuration);
builder.Services.AddSingleton(settings);
builder.Services.AddSingleton<IConnectionMultiplexer>(_ => ConnectionMultiplexer.Connect(settings.RedisConnectionString));
builder.Services.AddEndpointsApiExplorer();

var app = builder.Build();

app.Use(async (context, next) =>
{
    var requestId = context.Request.Headers["X-Request-Id"].FirstOrDefault() ?? Guid.NewGuid().ToString("N");
    context.Items["request_id"] = requestId;
    context.Response.Headers["X-Request-Id"] = requestId;
    await next();
});

await EnsureSchemaAsync(settings);

app.MapGet("/health/live", () => Results.Ok(new HealthResponse("ok")));

app.MapGet("/health/ready", async (IConnectionMultiplexer redis, AppSettings cfg) =>
{
    await using var db = OpenConnection(cfg.PostgresConnectionString);
    await db.ExecuteScalarAsync<int>("SELECT 1");
    await redis.GetDatabase().PingAsync();
    return Results.Ok(new HealthResponse("ready"));
});

app.MapGet("/v1/counters/{counterKey}", async (string counterKey, IConnectionMultiplexer redis, AppSettings cfg) =>
{
    var redisDb = redis.GetDatabase();
    var redisValue = await redisDb.StringGetAsync($"counter:{counterKey}");
    if (redisValue.HasValue && long.TryParse(redisValue.ToString(), out var cachedValue))
    {
        return Results.Ok(new CounterResponse(counterKey, cachedValue, null));
    }

    await using var db = OpenConnection(cfg.PostgresConnectionString);
    var counter = await db.QuerySingleOrDefaultAsync<CounterRecord>(
        "SELECT key AS Key, value AS Value, updated_at AS UpdatedAt FROM counters WHERE key = @Key",
        new { Key = counterKey });

    if (counter is null)
    {
        return Results.NotFound(new { detail = "counter not found" });
    }

    await redisDb.StringSetAsync($"counter:{counterKey}", counter.Value);
    return Results.Ok(new CounterResponse(counter.Key, counter.Value, counter.UpdatedAt));
});

app.MapPost("/v1/counters/{counterKey}/increment", async (
    string counterKey,
    IncrementRequest payload,
    HttpContext context,
    IConnectionMultiplexer redis,
    AppSettings cfg) =>
{
    var redisDb = redis.GetDatabase();
    var remoteIp = context.Connection.RemoteIpAddress?.ToString() ?? "unknown";
    var rateAllowed = await EnforceRateLimitAsync(redisDb, cfg, remoteIp);
    if (!rateAllowed)
    {
        return Results.Json(new { detail = "rate limit exceeded" }, statusCode: StatusCodes.Status429TooManyRequests);
    }

    if (payload.Delta < 1)
    {
        return Results.BadRequest(new { detail = "delta must be greater than or equal to 1" });
    }

    var idempotencyHeader = context.Request.Headers["Idempotency-Key"].FirstOrDefault();
    var redisIdempotencyKey = idempotencyHeader is null ? null : $"idem:{counterKey}:{idempotencyHeader}";

    if (redisIdempotencyKey is not null)
    {
        var cached = await redisDb.StringGetAsync(redisIdempotencyKey);
        if (cached.HasValue && long.TryParse(cached.ToString(), out var cachedValue))
        {
            return Results.Ok(new CounterResponse(counterKey, cachedValue, null));
        }
    }

    await using var db = OpenConnection(cfg.PostgresConnectionString);
    await using var tx = await db.BeginTransactionAsync();

    if (redisIdempotencyKey is not null)
    {
        var existing = await db.QuerySingleOrDefaultAsync<IdempotencyRecord>(
            "SELECT request_key AS RequestKey, response_value AS ResponseValue FROM idempotency_records WHERE request_key = @RequestKey",
            new { RequestKey = redisIdempotencyKey },
            tx);

        if (existing is not null)
        {
            await tx.CommitAsync();
            await redisDb.StringSetAsync(redisIdempotencyKey, existing.ResponseValue, TimeSpan.FromSeconds(cfg.IdempotencyTtlSeconds));
            return Results.Ok(new CounterResponse(counterKey, existing.ResponseValue, null));
        }
    }

    var updatedValue = await redisDb.StringIncrementAsync($"counter:{counterKey}", payload.Delta);
    var now = DateTimeOffset.UtcNow;

    const string upsertCounterSql = """
        INSERT INTO counters (key, value, updated_at)
        VALUES (@Key, @Value, @UpdatedAt)
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at;
        """;

    await db.ExecuteAsync(upsertCounterSql, new { Key = counterKey, Value = (long)updatedValue, UpdatedAt = now }, tx);

    if (redisIdempotencyKey is not null)
    {
        const string idempotencySql = """
            INSERT INTO idempotency_records (request_key, counter_key, response_value, created_at)
            VALUES (@RequestKey, @CounterKey, @ResponseValue, @CreatedAt)
            ON CONFLICT (request_key) DO NOTHING;
            """;

        await db.ExecuteAsync(idempotencySql, new
        {
            RequestKey = redisIdempotencyKey,
            CounterKey = counterKey,
            ResponseValue = (long)updatedValue,
            CreatedAt = now,
        }, tx);

        await redisDb.StringSetAsync(redisIdempotencyKey, (long)updatedValue, TimeSpan.FromSeconds(cfg.IdempotencyTtlSeconds));
    }

    await tx.CommitAsync();
    return Results.Ok(new CounterResponse(counterKey, (long)updatedValue, now));
});

app.Run();

static NpgsqlConnection OpenConnection(string connectionString)
{
    var connection = new NpgsqlConnection(connectionString);
    connection.Open();
    return connection;
}

static async Task EnsureSchemaAsync(AppSettings cfg)
{
    const string sql = """
        CREATE TABLE IF NOT EXISTS counters (
            key VARCHAR(255) PRIMARY KEY,
            value BIGINT NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS idempotency_records (
            id BIGSERIAL PRIMARY KEY,
            request_key VARCHAR(255) NOT NULL UNIQUE,
            counter_key VARCHAR(255) NOT NULL,
            response_value BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_idempotency_records_counter_key
            ON idempotency_records(counter_key);
        """;

    const int maxAttempts = 20;
    var delay = TimeSpan.FromSeconds(2);

    for (var attempt = 1; attempt <= maxAttempts; attempt++)
    {
        try
        {
            await using var connection = OpenConnection(cfg.PostgresConnectionString);
            await connection.ExecuteAsync(sql);
            return;
        }
        catch (Exception) when (attempt < maxAttempts)
        {
            await Task.Delay(delay);
        }
    }

    await using (var connection = OpenConnection(cfg.PostgresConnectionString))
    {
        await connection.ExecuteAsync(sql);
    }
}

static async Task<bool> EnforceRateLimitAsync(IDatabase redisDb, AppSettings cfg, string clientId)
{
    var rateLimitKey = $"ratelimit:{clientId}";
    var current = await redisDb.StringIncrementAsync(rateLimitKey);
    if (current == 1)
    {
        await redisDb.KeyExpireAsync(rateLimitKey, TimeSpan.FromSeconds(cfg.RateLimitWindowSeconds));
    }

    if (current > cfg.RateLimitMaxRequests)
    {
        return false;
    }

    return true;
}

sealed record HealthResponse(string Status);
sealed record IncrementRequest(long Delta = 1);
sealed record CounterResponse(string Key, long Value, DateTimeOffset? UpdatedAt);
sealed record CounterRecord(string Key, long Value, DateTimeOffset UpdatedAt);
sealed record IdempotencyRecord(string RequestKey, long ResponseValue);

sealed class AppSettings
{
    public required string PostgresConnectionString { get; init; }
    public required string RedisConnectionString { get; init; }
    public int IdempotencyTtlSeconds { get; init; } = 3600;
    public int RateLimitWindowSeconds { get; init; } = 60;
    public int RateLimitMaxRequests { get; init; } = 120;

    public static AppSettings FromConfiguration(IConfiguration configuration)
    {
        return new AppSettings
        {
            PostgresConnectionString = configuration["POSTGRES_CONNECTION_STRING"]
                ?? "Host=postgres;Port=5432;Database=counter;Username=postgres;Password=postgres",
            RedisConnectionString = configuration["REDIS_CONNECTION_STRING"] ?? "redis:6379",
            IdempotencyTtlSeconds = ReadInt(configuration, "IDEMPOTENCY_TTL_SECONDS", 3600),
            RateLimitWindowSeconds = ReadInt(configuration, "RATE_LIMIT_WINDOW_SECONDS", 60),
            RateLimitMaxRequests = ReadInt(configuration, "RATE_LIMIT_MAX_REQUESTS", 120),
        };
    }

    private static int ReadInt(IConfiguration configuration, string key, int defaultValue)
    {
        return int.TryParse(configuration[key], out var value) ? value : defaultValue;
    }
}
