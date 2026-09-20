# Cortafuegos de políticas

Source: docs/reference/guard.md
Last sync: 2026-09-20

[English](../../reference/guard.md) | [Español](guard.md)

`gitwise guard` es la puerta entre quien escribe en el repositorio y la base de
datos de objetos. Lee una política declarativa, emite un veredicto legible por
máquina e instala los hooks de git que hacen inevitable ese veredicto.

La distinción importa cuando quien escribe es un agente. Un guard que solo
corre dentro de `gitwise commit` no protege nada: el agente puede llamar a
`git commit` directamente y saltárselo. Los hooks cierran ese hueco.

## El archivo de política

La política vive en `.gitwise/policy.json`, dentro del repositorio. Es una
decisión deliberada: así se revisa en un pull request y la configuración global
de git de un desarrollador no puede debilitarla.

```json
{
  "version": 1,
  "protected_branches": ["main", "master"],
  "forbidden_paths": [".env", "*.pem", "secrets/**"],
  "commit_types": ["feat", "fix", "refactor", "docs", "chore", "test"],
  "require_gpg": true,
  "block_secrets": true,
  "allow_force_push": false,
  "block_direct_commits": false
}
```

Todas las claves son opcionales; lo que se omite cae al valor por defecto, así
que un repositorio sin archivo de política se comporta exactamente como antes.
El esquema está publicado en `share/schemas/v1/policy.json`.

| Clave | Por defecto | Efecto |
|---|---|---|
| `protected_branches` | `["main", "master"]` | Ramas protegidas contra reescrituras de historia: force push y borrado |
| `forbidden_paths` | `[]` | Globs fnmatch; una ruta en el índice que coincida bloquea el commit |
| `commit_types` | el conjunto conventional | Tipos de commit permitidos, verificados por el hook `commit-msg` |
| `require_gpg` | `false` | Bloquea si la firma GPG no está configurada y lista |
| `block_secrets` | `true` | Bloquea ante hallazgos de secretos de severidad alta; con `false` pasan a advertencia |
| `allow_force_push` | `false` | Permite push no-fast-forward a ramas protegidas |
| `block_direct_commits` | `false` | Además rechaza commits hechos directamente sobre una rama protegida |

Proteger una rama significa que no se reescribe, no que no se commitea.
Rechazar commits directos es una decisión de equipo aparte, y por eso tiene su
propia clave opt-in.

La carga falla cerrada. Un archivo malformado, una clave desconocida o un valor
del tipo equivocado son un error, nunca una degradación silenciosa a "todo
permitido".

## `gitwise guard check`

Evalúa la política e informa, sin modificar nada.

```bash
gitwise guard check                       # cambios en el índice
gitwise guard check --json                # veredicto legible por máquina
gitwise guard check --push                # actualizaciones de refs desde stdin
gitwise guard check --commit-msg .git/COMMIT_EDITMSG
gitwise guard check --quiet                # silencioso salvo que algo falle
```

Los códigos de salida separan política de fallo:

| Código | Significado |
|---|---|
| `0` | Nada bloquea |
| `2` | La política bloquea la operación |
| `1` | Error operativo: no es un repositorio, política ilegible |

Un hook colapsa ambos casos no-cero en "rechazado", pero un agente que decide
qué hacer a continuación necesita distinguirlos.

```json
{
  "v": 3,
  "ok": true,
  "command": "guard",
  "data": {
    "action": "check",
    "scope": "commit",
    "allowed": false,
    "violations": [
      {
        "rule": "forbidden_path",
        "severity": "block",
        "message": "deploy/key.pem matches a forbidden path in the repository policy",
        "path": "deploy/key.pem",
        "detail": null
      }
    ],
    "blocking_count": 1,
    "warning_count": 0,
    "policy_source": ".gitwise/policy.json"
  },
  "hints": [],
  "errors": []
}
```

Reglas: `protected_branch`, `forbidden_path`, `secret`,
`secret_scan_unavailable`, `gpg`, `commit_type`, `force_push`,
`protected_branch_delete`. Una violación nunca transporta la credencial en sí,
solo la regla que coincidió y dónde.

Un merge, rebase o cherry-pick en pausa deliberadamente no es una violación. El
commit que cierra un merge con conflictos es justo aquel para el que git
ejecuta el hook, así que rechazarlo dejaría al usuario sin poder terminar ni
abortar salvo con `--no-verify`. `gitwise commit` sigue rechazándolo por su
cuenta, que es donde la comprobación corresponde.

## `gitwise guard install`

Registra tres hooks que llaman a `guard check`:

| Hook | Qué rechaza |
|---|---|
| `pre-commit` | Rutas prohibidas, credenciales filtradas, GPG ausente |
| `commit-msg` | Un asunto cuyo tipo la política no permite |
| `pre-push` | Force push y borrado de ramas protegidas |

```bash
gitwise guard install --dry-run           # mostrar el plan
gitwise guard install --yes
gitwise guard install --uninstall --yes
```

Los backends siguen a `gitwise setup`: `--hooks-mode native` usa la
configuración `hook.<name>.command` de git (2.54 o superior), `legacy` apunta
`core.hooksPath` a los scripts incluidos, y el modo por defecto `preserve`
elige el que esté disponible. Si husky, lefthook o pre-commit ya gobiernan los
hooks del repositorio, la instalación se omite con una advertencia en lugar de
apropiárselos.

La instalación también verifica que los scripts tengan el bit de ejecución. Los
wheels no preservan de forma fiable los modos de archivo, y un hook que git no
puede ejecutar es protección que silenciosamente no corre.

## Uso desde un agente

```bash
gitwise guard check --json || handle_violations
```

El mismo veredicto respalda a `gitwise commit`, así que ambos caminos no pueden
divergir. `gitwise commit` conserva su confirmación interactiva de secretos, que
es más estricta: dejar pasar un hallazgo de severidad alta en modo `--json`
exige la variable de entorno `GITWISE_ALLOW_SECRETS`, que un prompt no puede
fijar.
