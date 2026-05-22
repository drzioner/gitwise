# Por que gitwise

Source: docs/why.md
Last sync: 2026-05-22

[English](../why.md) | [Espanol](why.md)

## El problema

Claude Code puede consumir contexto innecesario con operaciones Git verbosas:

- `git diff` sin `--stat` puede generar miles de lineas
- `git log` sin limite puede recorrer todo el historial
- no existe una politica nativa para forzar comandos compactos en cada ejecucion

Issue relacionado: [claude-code#21892](https://github.com/anthropics/claude-code/issues/21892).

## Solucion de gitwise

Tres capas de proteccion:

1. **CLAUDE.md** (`setup-agents`) con instrucciones para comandos compactos
2. **settings.json** (`setup-agents`) con allow/deny para comandos peligrosos
3. **core.hooksPath** (`setup`) con hooks Git para GPG y conventional commits

## Por que no depender de PreToolUse/PostToolUse

Issues [#6305](https://github.com/anthropics/claude-code/issues/6305),
[#24327](https://github.com/anthropics/claude-code/issues/24327),
[#34859](https://github.com/anthropics/claude-code/issues/34859) muestran que
los hooks no siempre ejecutan de forma confiable en macOS.

## Decisiones de diseno

Ver [AGENTS.md](../../AGENTS.md) para detalles de arquitectura.
