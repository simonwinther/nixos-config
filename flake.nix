{
  description = "Portable Hyprland workstation configurations";

  inputs = {
    self.submodules = true;
    ferry = {
      url = "git+ssh://git@github.com/simonwinther/ferry?ref=main&rev=14ec1449740c3fc2c82a3760485105a3aec088b7";
      flake = false;
    };
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    hyprland.url = "github:hyprwm/Hyprland/efb50993780079460b0cbed1363e2166a2de1d9f";
    hyprspace = {
      url = "github:simonwinther/hyprspace/4de74c8d5e3156b945319a76709e63e695aaddd7";
      inputs.hyprland.follows = "hyprland";
    };
    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    sops-nix = {
      url = "github:Mic92/sops-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nix-flatpak.url = "github:gmodena/nix-flatpak/v0.8.0";
    breakd = {
      url = "github:simonwinther/breakd/e912976591fe1e221676dfe2eba65ade82533ee2";
      inputs.nixpkgs.follows = "unstable";
    };
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      home-manager,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
      unstable = import inputs.unstable {
        inherit system;
        config.allowUnfree = true;
      };
      packages = import ./pkgs { inherit inputs pkgs unstable; };
      mkHost =
        host: profile:
        nixpkgs.lib.nixosSystem {
          inherit system;
          specialArgs = {
            inherit
              inputs
              packages
              unstable
              host
              profile
              ;
          };
          modules = [
            ./modules/nixos
            (./hosts + "/${host}")
            (./profiles + "/${profile}.nix")
            inputs.sops-nix.nixosModules.sops
            inputs.disko.nixosModules.disko
          ]
          ++ nixpkgs.lib.optionals (profile != "recovery") [
            home-manager.nixosModules.home-manager
            {
              nixpkgs.config.allowUnfree = true;
              home-manager = {
                useGlobalPkgs = true;
                useUserPackages = true;
                backupFileExtension = "before-nixos";
                extraSpecialArgs = {
                  inherit
                    inputs
                    packages
                    unstable
                    host
                    profile
                    ;
                };
                users.simon = import ./modules/home;
              };
            }
          ];
        };
    in
    {
      nixosConfigurations = {
        desktop = mkHost "desktop" "workstation";
        desktop-recovery = mkHost "desktop" "recovery";
        desktop-live = mkHost "desktop" "live";
        lambda = mkHost "lambda" "laptop";
      };
      packages.${system} = packages // {
        default = packages.desktop-tools;
        desktop-iso = self.nixosConfigurations.desktop-live.config.system.build.isoImage;
      };
      checks.${system} = import ./tests/checks.nix { inherit pkgs packages self; };
      formatter.${system} = pkgs.nixfmt;
      devShells.${system} = {
        roblox = pkgs.mkShellNoCC {
          packages = [
            packages.roblox-toolchain
            (pkgs.python3.withPackages (python: [ python.pillow ]))
          ];
          SPELL_ROBLOX_TYPES = "${packages.roblox-editor-resources}/globalTypes.d.luau";
        };
        default = pkgs.mkShell {
          packages = with pkgs; [
            nixfmt
            statix
            deadnix
            shellcheck
            python3
            stow
            lua
            luajit
            git
          ];
        };
        rust-desktop = pkgs.mkShell {
          nativeBuildInputs = with pkgs; [
            unstable.rustc
            unstable.cargo
            unstable.clippy
            unstable.rustfmt
            pkg-config
            cmake
            ninja
            python3
            git
            fd
          ];
          buildInputs = with pkgs; [
            gtk4
            gtk4-layer-shell
            sqlite
            libcanberra
            wayland
            pipewire
            alsa-lib
            openssl
            libxkbcommon
            fontconfig
            freetype
          ];
          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (
            with pkgs;
            [
              gtk4
              gtk4-layer-shell
              sqlite
              libcanberra
              wayland
              pipewire
              alsa-lib
              libxkbcommon
              fontconfig
              freetype
              libGL
              vulkan-loader
            ]
          );
          shellHook = ''
            export WORKSPACES_SLIDER_FONT="$(${pkgs.findutils}/bin/find ${pkgs.nerd-fonts.jetbrains-mono}/share/fonts -name JetBrainsMonoNerdFont-Bold.ttf -print -quit)"
          '';
        };
      };
    };
}
