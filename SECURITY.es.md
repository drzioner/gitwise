# Politica de Seguridad

Source: SECURITY.md
Last sync: 2026-07-21

[English](SECURITY.md) | [Español](SECURITY.es.md)

## Versiones soportadas

| Version | Soporte |
|---|---|
| Ultimo release | Si |
| Releases anteriores | No |

## Reportar una vulnerabilidad

**No reportes vulnerabilidades de seguridad en issues publicos de GitHub.**

Usa el canal privado de GitHub Security Advisories:

1. Ir a [github.com/drzioner/gitwise/security/advisories](https://github.com/drzioner/gitwise/security/advisories)
2. Click en "Report a vulnerability"
3. Completar detalles

Tambien puedes enviar email a **drzioner@gmail.com** con asunto `gitwise security: <descripcion breve>`.

### Que incluir

- Tipo de vulnerabilidad (ej. command injection, path traversal, privilege escalation)
- Pasos completos de reproduccion
- Versiones afectadas
- Impacto potencial
- Propuesta de solucion (si aplica)

### Tiempo de respuesta

- **Acuse de recibo**: dentro de 48 horas
- **Evaluacion inicial**: dentro de 7 dias
- **Fix y disclosure**: segun severidad, tipicamente en 30 dias

## Medidas de seguridad

gitwise incluye estas medidas:

- **Dependencias runtime minimas**: `rich`, `rich-argparse` y `shtab`; Git se ejecuta mediante subprocess.
- **Preservacion de firma**: `setup` y `setup-agents` no modifican `commit.gpgsign`, `user.signingkey` ni credenciales.
- **Guardas para agentes**: las reglas generadas bloquean flags conocidos para omitir firma y hooks.
- **Subprocess endurecidos**: se limpian variables de inyeccion de config/comandos Git y los procesos externos usan timeouts explicitos.
- **Escaneo de secretos**: `diff --scan-secrets` y `commit` detectan patrones de credenciales y redactan previews.
- **Symlinks con sandbox**: `_safe_create_symlink` protege contra TOCTOU y path traversal.
- **Actions pineadas**: las acciones core de terceros usan SHA inmutables.
- **Auditoria de dependencias y shell**: CI ejecuta pip-audit y shellcheck.
- **Proteccion de rama**: `main` requiere CI y review para contribuciones externas.
