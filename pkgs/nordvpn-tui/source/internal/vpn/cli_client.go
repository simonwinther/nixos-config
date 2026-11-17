package vpn

import "context"

// CLIClient is the real implementation that shells out to `nordvpn`.
type CLIClient struct{}

func NewCLIClient() *CLIClient { return &CLIClient{} }

func (c *CLIClient) Status(ctx context.Context) (Status, error) {
	out, err := run(ctx, "status")
	if err != nil {
		return Status{State: StateUnknown, Raw: out}, err
	}
	return ParseStatus(out), nil
}

func (c *CLIClient) Settings(ctx context.Context) (Settings, error) {
	out, err := run(ctx, "settings")
	if err != nil {
		return Settings{Raw: out}, err
	}
	return ParseSettings(out), nil
}

func (c *CLIClient) Account(ctx context.Context) (Account, error) {
	out, err := run(ctx, "account")
	if err != nil {
		return Account{Raw: out}, err
	}
	return ParseAccount(out), nil
}

func (c *CLIClient) Countries(ctx context.Context) ([]string, error) {
	out, err := run(ctx, "countries")
	if err != nil {
		return nil, err
	}
	return ParseList(out), nil
}

func (c *CLIClient) Cities(ctx context.Context, country string) ([]string, error) {
	out, err := run(ctx, "cities", Arg(country))
	if err != nil {
		return nil, err
	}
	return ParseList(out), nil
}

func (c *CLIClient) Connect(ctx context.Context) error {
	_, err := run(ctx, "connect")
	return err
}

func (c *CLIClient) ConnectCountry(ctx context.Context, country string) error {
	_, err := run(ctx, "connect", Arg(country))
	return err
}

func (c *CLIClient) ConnectCity(ctx context.Context, country, city string) error {
	_, err := run(ctx, "connect", Arg(country), Arg(city))
	return err
}

func (c *CLIClient) Disconnect(ctx context.Context) error {
	_, err := run(ctx, "disconnect")
	return err
}

func (c *CLIClient) Set(ctx context.Context, key, value string) error {
	_, err := run(ctx, "set", key, value)
	return err
}
