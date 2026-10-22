# Runtime secrets

No credentials were imported. Do not put plaintext keys, password hashes, recovery codes, browser profiles, private SSH keys, or account databases in this repository: Nix sources and derivations are readable in the store.

Bootstrap with mutable users, set Simon's password inside the installed system before the first reboot, and authenticate applications independently on the desktop. After testing an offline age recovery key, optionally enable `workstation.secrets` with an encrypted SOPS YAML file, an explicit recipient list in `.sops.yaml`, and `/var/lib/sops-nix/key.txt` installed as root with mode 0600.

The current module expects encrypted entries `simon-password-hash`, `dictate-env`, and `weather-key`. The hash is decrypted before user creation; the other entries become private runtime files at `~/.config/dictate/secrets.env` and `~/.config/desktop/secrets/weather-key`. Keep the age private key and a recovery copy outside the encrypted system disk. Encrypted files can be committed; keys cannot.

Without SOPS, provision those two runtime files manually as Simon, mode 0600. Dictation reads `secrets.env` in addition to the committed non-secret preferences. Hendrix credentials live in `~/.config/hendrix/`; Canvas in `~/.config/canvas-mcp/environment`. Provision these only after the new accounts and keyring work. Never copy another machine's lock-screen authentication or VPN daemon state as a substitute for login.

The reference also has private shell variables, Git credentials, `.netrc`, SSH configuration/keys, and application credential stores. They are accounted for by the private-state audit rather than copied into this repository. Preserve them in an independently verified encrypted backup and choose which identities to transfer; the desktop's browser, keyring, and VPN authentication remain independent.

Additional private files can be provisioned declaratively from named encrypted SOPS entries. For example, `workstation.secrets.additionalFiles.shell-env.path = "/home/simon/.config/zsh/secrets.zsh";` installs that encrypted entry at the existing shell's expected runtime path, owned by Simon with mode `0600`. The optional entries can also cover selected SSH keys or service environment files. Only configure files SOPS should own; helper-managed SSH configuration and account databases can remain privately restored mutable state. No additional entry is required or decrypted until explicitly configured, and no secret values are collected into this repository.
