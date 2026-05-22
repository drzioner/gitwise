# Politica de Seguridad

Source: SECURITY.md
Last sync: 2026-05-22

[English](SECURITY.md) | [Espanol](SECURITY.es.md)

## Versiones soportadas

| Version | Soporte |
|---|---|
| >= 0.1.0 | Si |
| < 0.1.0 | No |

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

- **Dependencias runtime minimas** — una dependencia runtime (`rich>=13.0`) y el resto stdlib + subprocess de git
- **Enforcement de firma GPG** — hook pre-commit valida disponibilidad de clave
- **Symlinks con sandbox** — `_safe_create_symlink` con proteccion TOCTOU y prevencion de path traversal
- **Sin secretos en codigo** — credenciales, tokens y claves no se almacenan ni loguean
- **Actions pineadas** — las acciones core de terceros en CI usan SHA, no tags mutables
- **pip-audit en CI** — escaneo continuo de vulnerabilidades en dependencias
- **shellcheck** — analisis estatico de scripts shell
- **Proteccion de rama** — `main` requiere CI y review para contribuciones externas
