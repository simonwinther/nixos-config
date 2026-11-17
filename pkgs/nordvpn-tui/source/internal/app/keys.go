package app

import "github.com/charmbracelet/bubbles/key"

// Global keymap. View-specific keys live with their views.
type KeyMap struct {
	Quit       key.Binding
	Help       key.Binding
	Log        key.Binding
	Back       key.Binding
	Home       key.Binding
	Countries  key.Binding
	Settings   key.Binding
	Connect    key.Binding
	Disconnect key.Binding
	Enter      key.Binding
	Search     key.Binding
	Up         key.Binding
	Down       key.Binding
	Right      key.Binding
	Left       key.Binding
}

func DefaultKeys() KeyMap {
	return KeyMap{
		Quit:       key.NewBinding(key.WithKeys("q", "ctrl+c"), key.WithHelp("q", "quit")),
		Help:       key.NewBinding(key.WithKeys("?"), key.WithHelp("?", "help")),
		Log:        key.NewBinding(key.WithKeys("L"), key.WithHelp("L", "log")),
		Back:       key.NewBinding(key.WithKeys("esc"), key.WithHelp("esc", "back")),
		Home:       key.NewBinding(key.WithKeys("1"), key.WithHelp("1", "home")),
		Countries:  key.NewBinding(key.WithKeys("2"), key.WithHelp("2", "countries")),
		Settings:   key.NewBinding(key.WithKeys("3"), key.WithHelp("3", "settings")),
		Connect:    key.NewBinding(key.WithKeys("c"), key.WithHelp("c", "connect")),
		Disconnect: key.NewBinding(key.WithKeys("d"), key.WithHelp("d", "disconnect")),
		Enter:      key.NewBinding(key.WithKeys("enter"), key.WithHelp("enter", "select")),
		Search:     key.NewBinding(key.WithKeys("/"), key.WithHelp("/", "search")),
		Up:         key.NewBinding(key.WithKeys("up", "k"), key.WithHelp("↑/k", "up")),
		Down:       key.NewBinding(key.WithKeys("down", "j"), key.WithHelp("↓/j", "down")),
		Right:      key.NewBinding(key.WithKeys("right", "l"), key.WithHelp("→/l", "forward")),
		Left:       key.NewBinding(key.WithKeys("left", "h"), key.WithHelp("←/h", "back")),
	}
}
