package log

import (
	"sync"
	"time"
)

type Level int

const (
	LevelInfo Level = iota
	LevelWarn
	LevelError
)

func (l Level) String() string {
	switch l {
	case LevelWarn:
		return "WARN"
	case LevelError:
		return "ERR "
	default:
		return "INFO"
	}
}

type Entry struct {
	Time    time.Time
	Level   Level
	Message string
}

// Buffer is a small thread-safe ring buffer of recent events.
type Buffer struct {
	mu   sync.Mutex
	size int
	buf  []Entry
}

func NewBuffer(size int) *Buffer {
	if size <= 0 {
		size = 50
	}
	return &Buffer{size: size, buf: make([]Entry, 0, size)}
}

func (b *Buffer) Add(level Level, msg string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	e := Entry{Time: time.Now(), Level: level, Message: msg}
	if len(b.buf) < b.size {
		b.buf = append(b.buf, e)
		return
	}
	copy(b.buf, b.buf[1:])
	b.buf[len(b.buf)-1] = e
}

func (b *Buffer) Info(msg string)  { b.Add(LevelInfo, msg) }
func (b *Buffer) Warn(msg string)  { b.Add(LevelWarn, msg) }
func (b *Buffer) Error(msg string) { b.Add(LevelError, msg) }

func (b *Buffer) Snapshot() []Entry {
	b.mu.Lock()
	defer b.mu.Unlock()
	out := make([]Entry, len(b.buf))
	copy(out, b.buf)
	return out
}
