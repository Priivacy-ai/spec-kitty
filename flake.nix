{
  description = "Spec Kitty - Specification Driven Development for AI agents";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    let
      # Extract version from pyproject.toml
      pyproject = builtins.fromTOML (builtins.readFile ./pyproject.toml);
      version = pyproject.project.version;

      # Package builder function that can be used in overlay
      mkSpecKitty =
        {
          pkgs,
          python3Packages ? pkgs.python3Packages,
        }:
        let
          # Override truststore to use version compatible with spec-kitty (>=0.10.4)
          truststore-compat = python3Packages.truststore.overridePythonAttrs (old: rec {
            version = "0.10.4";
            src = pkgs.fetchPypi {
              pname = "truststore";
              inherit version;
              sha256 = "00f3xc7720rkddsn291yrw871kfnimi6d9xbwi75xbb3ci1vv4cx";
            };
          });

          pythonEnv = python3Packages.python.withPackages (ps: [
            ps.httpx
            ps.packaging
            ps.platformdirs
            ps.psutil
            ps.pydantic
            ps.pyyaml
            ps.readchar
            ps.rich
            ps.ruamel-yaml
            ps.socksio
            truststore-compat
            ps.typer
            # Test dependencies
            ps.pytest
            ps.build
          ]);
        in
        python3Packages.buildPythonApplication rec {
          pname = "spec-kitty";
          inherit version;
          format = "pyproject";

          src = self;

          nativeBuildInputs = with python3Packages; [
            hatchling
            pip
            pkgs.makeWrapper
          ];

          propagatedBuildInputs = with python3Packages; [
            httpx
            packaging
            platformdirs
            psutil
            pydantic
            pyyaml
            readchar
            rich
            ruamel-yaml
            socksio
            truststore-compat
            typer
          ];

          nativeCheckInputs = with python3Packages; [
            pytest
            build
            pkgs.git
            pkgs.coreutils
            pkgs.lsof
          ];

          postInstall =
            let
              sitePackages = "$out/lib/${python3Packages.python.libPrefix}/site-packages";
              wrappedPython = "$out/bin/spec-kitty-python";
              wrappedBash = "$out/bin/spec-kitty-bash";
              envSitePackages = "${pythonEnv}/${python3Packages.python.sitePackages}";
              bashPath = pkgs.lib.makeBinPath [
                pkgs.git
                pkgs.coreutils
                pkgs.findutils
                pkgs.gnugrep
                pkgs.gnused
              ];
            in
            ''
              # Create a wrapped python3 that includes spec-kitty in its path
              makeWrapper ${pythonEnv}/bin/python3 ${wrappedPython} \
                --prefix PYTHONPATH : "${sitePackages}"

              # Create a wrapped bash that includes all dependencies in PATH
              makeWrapper ${pkgs.bash}/bin/bash ${wrappedBash} \
                --prefix PATH : "${bashPath}" \
                --prefix PATH : "$out/bin"

              # Patch pre-commit hook to use full path to spec-kitty
              substituteInPlace ${sitePackages}/specify_cli/templates/git-hooks/pre-commit-encoding-check \
                --replace-fail "command -v spec-kitty" "command -v $out/bin/spec-kitty" \
                --replace-fail "spec-kitty validate-encoding" "$out/bin/spec-kitty validate-encoding"

              # Patch all bash scripts: use wrapped bash shebang and wrapped python3
              for script in ${sitePackages}/specify_cli/scripts/bash/*.sh; do
                if [ -f "$script" ]; then
                  substituteInPlace "$script" \
                    --replace-quiet "#!/usr/bin/env bash" "#!${wrappedBash}" \
                    --replace-quiet "#!/bin/bash" "#!${wrappedBash}" \
                    --replace-quiet "python3 " "${wrappedPython} " \
                    --replace-quiet "command -v python3" "command -v ${wrappedPython}" \
                    --replace-quiet "python3 is required" "spec-kitty-python is required"
                fi
              done

              # Patch all powershell scripts similarly
              for script in ${sitePackages}/specify_cli/scripts/powershell/*.ps1; do
                if [ -f "$script" ]; then
                  substituteInPlace "$script" \
                    --replace-quiet "python3 " "${wrappedPython} "
                fi
              done

              # Patch standalone Python scripts with proper shebang
              for script in ${sitePackages}/specify_cli/scripts/*.py; do
                if [ -f "$script" ]; then
                  substituteInPlace "$script" \
                    --replace-quiet "#!/usr/bin/env python3" "#!${wrappedPython}" \
                    --replace-quiet "#!/usr/bin/env python" "#!${wrappedPython}"
                fi
              done

              # Patch Python scripts in tasks directory
              for script in ${sitePackages}/specify_cli/scripts/tasks/*.py; do
                if [ -f "$script" ]; then
                  substituteInPlace "$script" \
                    --replace-quiet "#!/usr/bin/env python3" "#!${wrappedPython}" \
                    --replace-quiet "#!/usr/bin/env python" "#!${wrappedPython}"
                fi
              done

              # Patch markdown command templates to include path setup before specify_cli imports
              local pathSetup="import sys; sys.path.insert(0, '${envSitePackages}'); sys.path.insert(0, '${sitePackages}'); "

              find ${sitePackages}/specify_cli -name "*.md" -type f | while read -r mdfile; do
                if grep -q "from specify_cli" "$mdfile" 2>/dev/null; then
                  substituteInPlace "$mdfile" \
                    --replace-quiet "from specify_cli" "''${pathSetup}from specify_cli"
                fi
              done
            '';

          # Enable the test suite
          doCheck = true;

          checkPhase = ''
            runHook preCheck

            # Set up git config for tests that use git
            export HOME=$(mktemp -d)
            git config --global user.name "Nix Build"
            git config --global user.email "nix@localhost"
            git config --global init.defaultBranch main

            # Create a fake venv directory to satisfy the test_venv fixture
            # The fixture checks if VERSION file matches pyproject.toml version
            # If it exists and matches, it skips venv creation (which needs network)
            VENV_DIR=".pytest_cache/spec-kitty-test-venv"
            mkdir -p "$VENV_DIR/bin"
            echo "${version}" > "$VENV_DIR/VERSION"

            # Create wrapper scripts that include the source in PYTHONPATH
            # This is needed because tests run 'python -m specify_cli' from the fake venv
            cat > "$VENV_DIR/bin/python" << EOF
            #!/bin/sh
            export PYTHONPATH="$PWD/src:\$PYTHONPATH"
            exec ${pythonEnv}/bin/python3 "\$@"
            EOF
            chmod +x "$VENV_DIR/bin/python"

            ln -sf "$VENV_DIR/bin/python" "$VENV_DIR/bin/python3"
            ln -sf ${pythonEnv}/bin/pip "$VENV_DIR/bin/pip"

            # Set the environment variable so the fixture finds our fake venv
            export SPEC_KITTY_TEST_VENV="$PWD/$VENV_DIR"

            # Add src to PYTHONPATH so 'python -m specify_cli' works
            export PYTHONPATH="$PWD/src:$PYTHONPATH"

            # Run pytest, skipping tests that require network, wheel installation, or CLI in PATH
            pytest tests/ \
                -m "not distribution and not slow" \
                --ignore=tests/release/ \
                --ignore=tests/adversarial/test_distribution.py \
                --ignore=tests/specify_cli/orchestrator/test_quickstart.py \
                --ignore=tests/test_version_detection.py \
                -x \
                -v

            runHook postCheck
          '';

          # Keep the installation checks as well
          doInstallCheck = true;

          installCheckPhase =
            let
              sitePackages = "$out/lib/${python3Packages.python.libPrefix}/site-packages";
              envSitePackages = "${pythonEnv}/${python3Packages.python.sitePackages}";
            in
            ''
              runHook preInstallCheck

              echo "=== Testing spec-kitty installation ==="

              # Test 1: Main CLI works
              echo "Test 1: spec-kitty CLI..."
              $out/bin/spec-kitty --version
              $out/bin/spec-kitty --help >/dev/null

              # Test 2: spec-kitty-python wrapper exists and works
              echo "Test 2: spec-kitty-python wrapper..."
              test -x $out/bin/spec-kitty-python
              $out/bin/spec-kitty-python --version

              # Test 2b: spec-kitty-bash wrapper exists and has dependencies
              echo "Test 2b: spec-kitty-bash wrapper..."
              test -x $out/bin/spec-kitty-bash
              $out/bin/spec-kitty-bash -c "command -v git"
              $out/bin/spec-kitty-bash -c "command -v spec-kitty-python"
              $out/bin/spec-kitty-bash -c "command -v find"
              $out/bin/spec-kitty-bash -c "command -v grep"
              $out/bin/spec-kitty-bash -c "command -v sed"
              echo "  spec-kitty-bash: dependencies OK"

              # Test 3: Python imports work through wrapper
              echo "Test 3: Python imports via wrapper..."
              $out/bin/spec-kitty-python -c "from specify_cli.guards import validate_worktree_location"
              $out/bin/spec-kitty-python -c "from specify_cli.mission import get_mission_for_feature"
              $out/bin/spec-kitty-python -c "from specify_cli.dashboard.scanner import scan_all_features"
              $out/bin/spec-kitty-python -c "import specify_cli; print('All imports OK')"

              # Test 4: Python imports work with inline path setup (simulating template execution)
              echo "Test 4: Template-style inline imports..."
              ${python3Packages.python}/bin/python3 -c "
              import sys
              sys.path.insert(0, '${envSitePackages}')
              sys.path.insert(0, '${sitePackages}')
              from specify_cli.guards import validate_worktree_location
              from specify_cli.mission import get_mission_for_feature
              print('Template imports OK')
              "

              # Test 5: Bash scripts are properly patched
              echo "Test 5: Bash script patching..."
              for script in ${sitePackages}/specify_cli/scripts/bash/*.sh; do
                scriptname=$(basename "$script")
                shebang=$(head -1 "$script")

                if echo "$shebang" | grep -q "^#!/usr/bin/env bash" || echo "$shebang" | grep -q "^#!/bin/bash"; then
                  echo "FAIL: $scriptname has unpatched bash shebang: $shebang"
                  exit 1
                fi
                if echo "$shebang" | grep -q "spec-kitty-bash"; then
                  echo "  $scriptname: shebang OK"
                fi

                if grep -E "^[^#]*command -v python3" "$script" 2>/dev/null; then
                  echo "FAIL: $scriptname still has unpatched 'command -v python3'"
                  exit 1
                fi
                if grep -q "python" "$script"; then
                  if grep -E "^[^#]*python3 " "$script" | grep -v "spec-kitty-python" >/dev/null 2>&1; then
                    echo "FAIL: $scriptname has unpatched python3 calls"
                    exit 1
                  fi
                fi
              done

              # Test 6: Markdown templates are patched with path setup
              echo "Test 6: Markdown template patching..."
              patched_count=0
              for mdfile in $(find ${sitePackages}/specify_cli -name "*.md" -type f); do
                if grep -q "from specify_cli" "$mdfile" 2>/dev/null; then
                  if ! grep -q "sys.path.insert" "$mdfile"; then
                    echo "FAIL: $(basename "$mdfile") has 'from specify_cli' but no path setup"
                    exit 1
                  fi
                  patched_count=$((patched_count + 1))
                fi
              done
              echo "  $patched_count markdown files with specify_cli imports are patched"

              # Test 7: Python task scripts have correct shebang
              echo "Test 7: Python script shebangs..."
              for script in ${sitePackages}/specify_cli/scripts/*.py ${sitePackages}/specify_cli/scripts/tasks/*.py; do
                if [ -f "$script" ]; then
                  scriptname=$(basename "$script")
                  shebang=$(head -1 "$script")
                  if echo "$shebang" | grep -q "^#!.*python"; then
                    if echo "$shebang" | grep -q "spec-kitty-python"; then
                      echo "  $scriptname: shebang OK"
                    else
                      echo "FAIL: $scriptname has unpatched python shebang: $shebang"
                      exit 1
                    fi
                  fi
                fi
              done

              # Test 8: Pre-commit hook is patched
              echo "Test 8: Pre-commit hook patching..."
              hook="${sitePackages}/specify_cli/templates/git-hooks/pre-commit-encoding-check"
              if [ -f "$hook" ]; then
                if grep -q "command -v spec-kitty" "$hook" | grep -v "$out/bin/spec-kitty"; then
                  if ! grep -q "$out/bin/spec-kitty" "$hook"; then
                    echo "FAIL: pre-commit hook not patched with full path"
                    exit 1
                  fi
                fi
                echo "  pre-commit-encoding-check: patched OK"
              fi

              # Test 9: Task helper modules can be imported
              echo "Test 9: Task helper modules..."
              $out/bin/spec-kitty-python -c "
              import sys
              sys.path.insert(0, '${sitePackages}/specify_cli/scripts/tasks')
              from task_helpers import LANES, WorkPackage
              from acceptance_support import AcceptanceResult
              print('Task helpers OK')
              "

              echo "=== All tests passed ==="

              runHook postInstallCheck
            '';

          pythonImportsCheck = [
            "specify_cli"
            "specify_cli.guards"
            "specify_cli.mission"
            "specify_cli.dashboard"
            "specify_cli.cli"
            "specify_cli.core"
            "specify_cli.template"
          ];

          meta = with pkgs.lib; {
            description = "Spec Kitty - Specification Driven Development for AI agents with kanban and git worktree isolation";
            homepage = "https://github.com/Priivacy-ai/spec-kitty";
            license = licenses.mit;
            maintainers = [ ];
            mainProgram = "spec-kitty";
          };
        };
    in
    {
      # Overlay for use in other flakes
      overlays.default = final: prev: {
        spec-kitty = mkSpecKitty {
          pkgs = final;
          python3Packages = final.python3Packages;
        };
      };

      # Also export the overlay under a named attribute
      overlays.spec-kitty = self.overlays.default;
    }
    // flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        spec-kitty = mkSpecKitty {
          inherit pkgs;
          python3Packages = pkgs.python3Packages;
        };
      in
      {
        packages = {
          default = spec-kitty;
          spec-kitty = spec-kitty;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            spec-kitty
            pkgs.python3
            pkgs.git
          ];

          shellHook = ''
            echo "spec-kitty development shell"
            echo "Run 'spec-kitty --version' to verify installation"
          '';
        };

        # Allow running directly with 'nix run'
        apps.default = {
          type = "app";
          program = "${spec-kitty}/bin/spec-kitty";
        };
      }
    );
}
