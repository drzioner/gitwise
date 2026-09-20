Source: docs/MIGRATION-0.36.md
Last sync: 2026-09-20

# Guía de migración (0.36)

0.36 estandariza el contrato de máquina y estrecha la superficie del producto.
El proyecto está pre-1.0 y en desarrollo activo, así que la decisión fue
corregir las inconsistencias ahora y anunciarlas, en lugar de arrastrarlas
hasta 1.0.

Todo lo que sigue rompe a propósito. Nada cambió por accidente.

## 1. `setup-agents --json` usa el envelope canónico

`setup-agents` era el único de los 31 comandos que ponía sus campos en el nivel
superior. Además declaraba una versión de esquema propia (`v_compat`), así que
un consumidor escrito contra cualquier otro comando fallaba con este.

**Antes:**

```json
{
  "v": 3,
  "v_compat": [1, 2, 3],
  "command": "setup-agents",
  "ok": true,
  "bucket": 2,
  "mode": "local",
  "actions": [...],
  "errors": ["algo falló"]
}
```

**Ahora:**

```json
{
  "v": 3,
  "ok": true,
  "command": "setup-agents",
  "data": {
    "bucket": 2,
    "mode": "local",
    "actions": [...]
  },
  "hints": [],
  "errors": [{ "code": "setup_agents_plan_failed", "message": "algo falló" }]
}
```

**Qué cambiar:** leer los campos de dominio desde `data`, y leer
`errors[].message` en vez de tratar `errors` como lista de cadenas. `v_compat`
desaparece; la versión del envelope es `v`, como en todos los demás.

El esquema publicado en `share/schemas/v1/output/setup-agents.json` describe la
forma nueva, y un test valida la salida real contra él.

## 2. La superficie legacy de `adapters` desaparece

| Retirado | Usar en su lugar |
|---|---|
| `--adapters` | `--providers` |
| `--list-adapters` | `--list-providers` |
| la clave `adapters` en `--list-providers --json` | la clave `providers` |

Los flags eran alias ocultos mantenidos por compatibilidad desde 0.17.
Invocarlos ahora falla con código 2 y un envelope `invalid_arguments`.

## 3. Diecisiete wrappers quedan ocultos y deprecados

`log`, `show`, `status`, `stash`, `tag`, `pick`, `undo`, `branches`, `sync`,
`merge`, `pr`, `clean`, `optimize`, `health`, `suggest`, `snapshot` y `update`
ya no aparecen en `gitwise --help`.

Siguen funcionando, y siguen aceptando sus alias. Cada uno imprime un aviso de
deprecación en stderr con su reemplazo, y `gitwise commands --json` informa de
`deprecated: true` más una cadena `replacement` por comando. Se eliminarán en
1.0.

**Qué cambiar:** nada todavía, pero conviene migrar al reemplazo que indica el
aviso. gitwise es una capa de política sobre cuatro comandos (`guard`, `commit`,
`worktree`, `setup-agents`); no busca paridad con `git` ni con `gh`.

## 4. Las rutas no-ASCII se reportan crudas

gitwise ejecuta git con `core.quotePath=false`. Antes, cualquier ruta con un
byte no-ASCII volvía entrecomillada y escapada en octal:

```
"configuraci\303\263n/.env"      # antes
configuración/.env               # ahora
```

Afectaba a las rutas que reportan `diff`, `log`, `show`, `conflicts`, `health` y
`context`, y en el motor de políticas era un bypass: un secreto bajo un
directorio con acento no coincidía con `forbidden_paths`.

**Qué cambiar:** si desescapabas esas cadenas por tu cuenta, deja de hacerlo. Si
comparabas contra la forma entrecomillada, compara contra la ruta real.

## 5. Los errores de argumentos responden en JSON

Un flag inválido salía con código 2, el usage en stderr y **nada** en stdout, en
todos los comandos. Con `--json` ahora emite además un envelope v3 con
`code: "invalid_arguments"`. El código de salida no cambia, y `--help` sigue
saliendo 0 sin envelope.

**Qué cambiar:** nada. El manejo de errores que esperaba stdout vacío ante un
argumento inválido sigue funcionando, pero ahora puedes parsear el fallo como
cualquier otro.

## 6. El motor de políticas ya no bloquea por operación en pausa

Si usabas `gitwise guard check` desde la 0.36-rc y dependías de la regla
`in_progress`, ya no está en el motor. Hacía imposible terminar un merge con
conflictos una vez instalados los hooks: el commit que cierra el merge es aquel
para el que git ejecuta el hook. `gitwise commit` sigue rechazando mientras hay
una operación en pausa, que es donde esa comprobación corresponde.

## 7. `supports_config_hooks` exige git 2.54

Los hooks por configuración (`hook.<name>.command`) solo los dispara git desde
2.54. gitwise comprobaba 2.36, la versión que introdujo el subcomando
`git hook run`, así que `setup --hooks-mode native` podía escribir
configuración que nunca se ejecutaba en git 2.36 a 2.53.

**Qué cambiar:** en git anterior a 2.54, usa `--hooks-mode legacy`, que el modo
por defecto `preserve` selecciona automáticamente.
