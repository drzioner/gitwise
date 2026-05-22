# Contribuir a gitwise

Source: CONTRIBUTING.md
Last sync: 2026-05-22

[English](CONTRIBUTING.md) | [Espanol](CONTRIBUTING.es.md)

Gracias por tu interes. Esta guia cubre lo necesario para contribuir.

## Inicio rapido

```bash
git clone https://github.com/drzioner/gitwise.git
cd gitwise
uv sync                            # crea .venv con dependencias de desarrollo
brew install lefthook               # instala el gestor de hooks
lefthook install                    # instala hooks de git
uv run pytest                      # corre toda la suite
uv run pytest -k test_worktree     # corre tests especificos
```

No hay paso de instalacion durante desarrollo. Ejecuta desde la raiz del repo:

```bash
python -m gitwise <command>
```

## Flujo de desarrollo

1. Crea una rama: `gitwise worktree new feature/my-thing` (o `git checkout -b`)
2. Realiza cambios
3. Los hooks corren automaticamente con lefthook:
   - **pre-commit**: ruff check + ruff format + shellcheck
   - **commit-msg**: validacion de conventional commits con commitizen
   - **pre-push**: suite completa de tests

Para ejecutar manualmente:

```bash
lefthook run pre-commit
lefthook run commit-msg --commit-msg-file .git/COMMIT_EDITMSG
lefthook run pre-push
```

4. Commit con formato convencional: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
5. Abre un pull request

## Arquitectura

Cada subcomando sigue el mismo patron:

```python
def run_<command>(...) -> int:   # retorna codigo de salida
    # 1. Validate (is_repo, repo_root)
    # 2. Plan (_plan_actions -> list[dict], warnings, errors)
    # 3. Dry-run: print plan, return 0
    # 4. Confirm (unless --yes)
    # 5. Execute (_execute_actions)
    # 6. Return exit code (0=ok, 1=error, 2=strict warnings)
```

Un modulo por subcomando en `gitwise/`. En `tests/`, la estructura espeja a
los modulos. Las pruebas invocan gitwise como subprocess via `run_gitwise()`
en `conftest.py`; no se usan mocks.

## Estilo de codigo

- Type hints en todas las firmas
- `pathlib.Path` sobre `os.path` (usar `os.path.realpath` para symlinks)
- Comentarios solo para explicar el POR QUE
- Dependencias minimas (`rich` es la unica runtime externa)
- `ruff` para lint y format (`pyproject.toml`)
- `lefthook` para hooks (`lefthook.yml`)
- `commitizen` para validar mensajes (`pyproject.toml`)

## Archivos clave

```
gitwise/             # paquete Python — un modulo por subcomando
  __main__.py        # router argparse -> dispatch a run_<cmd>()
  setup_agents/      # coexistencia AGENTS.md/CLAUDE.md (modelo 5 buckets)
  _cli_setup_agents.py  # adaptador CLI para setup-agents
  git.py             # helpers de subprocess para git
  output.py          # funciones de salida + confirm()
  snapshot.py        # genera .claude/git-snapshot.md
  doctor.py          # checks de entorno
  audit.py           # diagnosticos de repo
  setup.py           # defaults modernos de git
  clean.py           # limpieza de ramas/refs stale
  optimize.py        # gc, pack-refs, commit-graph
  summarize.py       # status + log compacto
  diff.py            # lista enfocada de cambios
  worktree.py        # helpers de worktree para agentes
share/claude/        # templates copiados/mergeados en repos target
share/hooks/         # hooks de Git (pre-commit, commit-msg)
tests/               # pytest — espejo de modulos
bin/gitwise          # wrapper shell -> python -m gitwise
install.sh           # instala en ~/.local/bin
```

## Proceso de pull request

- CI debe pasar (ruff, pytest, basedpyright, shellcheck)
- PRs de externos requieren al menos una review
- Se prefiere squash merge para mantener historia limpia
- Mantener PRs enfocados (una feature o fix por PR)
- Si cambias docs, actualiza ingles canonico y espejo en espanol

## Reporte de issues

- Usa [GitHub Issues](https://github.com/drzioner/gitwise/issues)
- Incluye: OS, version de Python, version de git y pasos de reproduccion
- Ejecuta `gitwise doctor` y adjunta salida
