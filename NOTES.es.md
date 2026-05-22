# Notas de diseno

Source: NOTES.md
Last sync: 2026-05-22

[English](NOTES.md) | [Espanol](NOTES.es.md)

## Stack: paquete Python + entry-point Bash corto

Alternativa evaluada: Bash puro. Se descarto porque `clean --branches` y `setup`
requieren mejor manejo de errores, pathlib y tests con pytest. El startup de
Python (~50ms) no es relevante para una CLI interactiva.

## Enforcement GPG: core.hooksPath, no hooks de Claude Code

Issues `#6305` y `#24327` muestran que PreToolUse/PostToolUse no siempre son
confiables en macOS. La proteccion GPG vive en `share/hooks/pre-commit`,
instalado via `core.hooksPath`.

`setup` nunca modifica `commit.gpgsign`; solo reporta estado.

## setup-agents vs setup: separacion intencional

`setup-agents` genera archivos estaticos (`CLAUDE.md`, `settings.json`, comandos slash).
`setup` modifica config de git (`fetch.prune`, `diff.algorithm`, etc.).
Se pueden usar de forma independiente.

## summarize y context son complementarios

`summarize` y `context` estan soportados.

- `summarize` se enfoca en status + historial compacto para uso diario.
- `context` entrega snapshot enriquecido para flujos con LLM.

Mantener ambos evita mezclar dos intenciones distintas en un solo comando.

## eza no se usa para listar ramas

`eza` es para listar directorios con color. Para ramas, la salida estructurada
en Python es mas apropiada.

## fsmonitor: solo macOS/Windows

`git config core.fsmonitor true` no tiene backend estable en Linux. `setup`
detecta `platform.system()` antes de aplicar.

## feature.manyFiles: habilitado solo con git >= 2.40

`feature.manyFiles=true` puede romper clientes Git antiguos. `setup` valida
version antes de aplicar.

## Audit log: XDG, no .git/

`.git/gitwise-audit.log` se pierde en ciertos flujos. El log se guarda en
`~/.local/share/gitwise/audit.log` siguiendo XDG.

## Tests: --no-gpg-sign solo en fixtures sinteticos

Fixtures usan `git commit --no-gpg-sign` en repos temporales. En repos reales,
`commit.gpgsign=true` queda protegido por hook.

## bat/delta: IS_TTY como gate

`bat_pipe()` en `output.py` revisa `IS_TTY` antes de invocar subprocess.
Esto evita ejecutar bat en tests sin TTY o salidas pipeadas.

- `summarize`: log -> `Git Log`, status -> `Git Output`
- `audit`: findings -> `Markdown`
