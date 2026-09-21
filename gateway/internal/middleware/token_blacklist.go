package middleware

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"net/url"
	"strconv"
	"strings"
	"time"
)

const tokenBlacklistPrefix = "token_blacklist:"

// TokenBlacklistChecker checks whether a token JTI has been revoked.
type TokenBlacklistChecker interface {
	IsBlacklisted(ctx context.Context, tokenID string) (bool, error)
}

// RedisTokenBlacklistChecker checks revoked tokens in Redis.
type RedisTokenBlacklistChecker struct {
	client *redisClient
}

// NewRedisTokenBlacklistChecker creates a Redis-backed blacklist checker.
func NewRedisTokenBlacklistChecker(redisURL string) (*RedisTokenBlacklistChecker, error) {
	client, err := newRedisClient(redisURL)
	if err != nil {
		return nil, err
	}

	return &RedisTokenBlacklistChecker{client: client}, nil
}

// IsBlacklisted returns true when the given token JTI exists in Redis.
func (c *RedisTokenBlacklistChecker) IsBlacklisted(ctx context.Context, tokenID string) (bool, error) {
	if c == nil || c.client == nil || tokenID == "" {
		return false, nil
	}

	value, err := c.client.Get(ctx, tokenBlacklistPrefix+tokenID)
	if err != nil {
		if errors.Is(err, errRedisNil) {
			return false, nil
		}
		return false, err
	}

	return value != "", nil
}

var errRedisNil = errors.New("redis nil")

type redisClient struct {
	address     string
	password    string
	database    int
	dialTimeout time.Duration
	ioTimeout   time.Duration
}

func newRedisClient(rawURL string) (*redisClient, error) {
	if rawURL == "" {
		return nil, fmt.Errorf("redis url is required")
	}

	parsed, err := url.Parse(rawURL)
	if err != nil {
		return nil, fmt.Errorf("parse redis url: %w", err)
	}

	if parsed.Scheme != "redis" {
		return nil, fmt.Errorf("unsupported redis scheme %q", parsed.Scheme)
	}

	address := parsed.Host
	if address == "" {
		address = "localhost:6379"
	}
	if !strings.Contains(address, ":") {
		address += ":6379"
	}

	database := 0
	if parsed.Path != "" && parsed.Path != "/" {
		dbValue := strings.TrimPrefix(parsed.Path, "/")
		database, err = strconv.Atoi(dbValue)
		if err != nil {
			return nil, fmt.Errorf("invalid redis database %q: %w", dbValue, err)
		}
	}

	password, _ := parsed.User.Password()

	return &redisClient{
		address:     address,
		password:    password,
		database:    database,
		dialTimeout: 2 * time.Second,
		ioTimeout:   2 * time.Second,
	}, nil
}

func (c *redisClient) Get(ctx context.Context, key string) (string, error) {
	conn, err := net.DialTimeout("tcp", c.address, c.dialTimeout)
	if err != nil {
		return "", fmt.Errorf("connect redis: %w", err)
	}
	defer func() { _ = conn.Close() }()

	deadline := time.Now().Add(c.ioTimeout)
	if ctxDeadline, ok := ctx.Deadline(); ok {
		deadline = ctxDeadline
	}
	if err := conn.SetDeadline(deadline); err != nil {
		return "", fmt.Errorf("set redis deadline: %w", err)
	}

	reader := bufio.NewReader(conn)

	if c.password != "" {
		if err := writeRedisCommand(conn, "AUTH", c.password); err != nil {
			return "", err
		}
		if _, err := readRedisResponse(reader); err != nil {
			return "", err
		}
	}

	if c.database != 0 {
		if err := writeRedisCommand(conn, "SELECT", strconv.Itoa(c.database)); err != nil {
			return "", err
		}
		if _, err := readRedisResponse(reader); err != nil {
			return "", err
		}
	}

	if err := writeRedisCommand(conn, "GET", key); err != nil {
		return "", err
	}

	return readRedisResponse(reader)
}

func writeRedisCommand(conn net.Conn, parts ...string) error {
	var builder strings.Builder
	builder.WriteString(fmt.Sprintf("*%d\r\n", len(parts)))
	for _, part := range parts {
		builder.WriteString(fmt.Sprintf("$%d\r\n%s\r\n", len(part), part))
	}

	if _, err := conn.Write([]byte(builder.String())); err != nil {
		return fmt.Errorf("write redis command: %w", err)
	}

	return nil
}

func readRedisResponse(reader *bufio.Reader) (string, error) {
	prefix, err := reader.ReadByte()
	if err != nil {
		return "", fmt.Errorf("read redis response prefix: %w", err)
	}

	line, err := reader.ReadString('\n')
	if err != nil {
		return "", fmt.Errorf("read redis response line: %w", err)
	}

	line = strings.TrimSuffix(strings.TrimSuffix(line, "\n"), "\r")

	switch prefix {
	case '+':
		return line, nil
	case '-':
		return "", fmt.Errorf("redis error: %s", line)
	case '$':
		length, err := strconv.Atoi(line)
		if err != nil {
			return "", fmt.Errorf("invalid redis bulk length %q: %w", line, err)
		}
		if length == -1 {
			return "", errRedisNil
		}

		payload := make([]byte, length+2)
		if _, err := io.ReadFull(reader, payload); err != nil {
			return "", fmt.Errorf("read redis bulk payload: %w", err)
		}

		return string(payload[:length]), nil
	default:
		return "", fmt.Errorf("unsupported redis response type %q", prefix)
	}
}
