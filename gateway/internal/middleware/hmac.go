package middleware

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"time"
)

const (
	// ServiceSignatureHeader carries the HMAC signature trusted by backend services.
	ServiceSignatureHeader = "X-Service-Signature"
	// ServiceTimestampHeader carries the unix timestamp used in the HMAC payload.
	ServiceTimestampHeader = "X-Service-Timestamp"
)

func computeBodyHash(body []byte) string {
	sum := sha256.Sum256(body)
	return hex.EncodeToString(sum[:])
}

func signaturePayload(method string, path string, timestamp int64, bodyHash string) []byte {
	return []byte(fmt.Sprintf("%s\n%s\n%d\n%s", method, path, timestamp, bodyHash))
}

// SignRequest adds the inter-service HMAC headers expected by backend services.
func SignRequest(req *http.Request, secret string) error {
	if secret == "" {
		return fmt.Errorf("missing inter-service secret")
	}

	body, err := readAndRestoreBody(req)
	if err != nil {
		return err
	}

	timestamp := time.Now().Unix()
	bodyHash := computeBodyHash(body)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(signaturePayload(req.Method, req.URL.Path, timestamp, bodyHash))
	signature := hex.EncodeToString(mac.Sum(nil))

	req.Header.Set(ServiceTimestampHeader, strconv.FormatInt(timestamp, 10))
	req.Header.Set(ServiceSignatureHeader, signature)
	return nil
}

func readAndRestoreBody(req *http.Request) ([]byte, error) {
	if req.Body == nil {
		req.GetBody = func() (io.ReadCloser, error) {
			return io.NopCloser(bytes.NewReader(nil)), nil
		}
		return nil, nil
	}

	body, err := io.ReadAll(req.Body)
	if err != nil {
		return nil, err
	}

	req.Body = io.NopCloser(bytes.NewReader(body))
	req.GetBody = func() (io.ReadCloser, error) {
		return io.NopCloser(bytes.NewReader(body)), nil
	}

	return body, nil
}
