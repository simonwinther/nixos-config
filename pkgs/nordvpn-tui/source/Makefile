BINARY  := nordvpn-tui
PKG     := ./...
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
COMMIT  := $(shell git rev-parse --short HEAD 2>/dev/null || echo none)
DATE    := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS := -X main.version=$(VERSION) -X main.commit=$(COMMIT) -X main.date=$(DATE)

.PHONY: build run run-fake test lint fmt tidy snapshot clean

build:
	go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY) ./cmd/nordvpn-tui

run: build
	./bin/$(BINARY)

run-fake: build
	./bin/$(BINARY) --fake

test:
	go test $(PKG)

lint:
	golangci-lint run

fmt:
	gofmt -w .

tidy:
	go mod tidy

snapshot:
	goreleaser release --snapshot --clean

clean:
	rm -rf bin dist
