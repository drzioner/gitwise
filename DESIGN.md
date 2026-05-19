# Design System: gitwise

## 1. Visual Theme & Atmosphere

gitwise embodies a **terminal-native, utilitarian aesthetic** rooted in the visual language of developer tools and code editors. The interface feels **dense yet deliberate**, prioritizing information hierarchy over decorative elements. The design philosophy is output-first, mimicking the clarity and structure of well-formatted terminal output.

The overall mood is **technical and authoritative**, creating a command-line identity that remains approachable to developers familiar with modern CLI tools. The atmosphere evokes the focused precision of a well-configured terminal session where every character serves a purpose.

**Key Characteristics:**
- Monospaced typography reinforcing the CLI and coding nature of the brand
- High-contrast readability optimized for both light and dark viewing contexts
- Minimalist ornamentation — function dictates form
- Bracket `[ ]` and cursor motifs as recurring visual anchors
- Sharp 90-degree corners reflecting a grid-based terminal system
- Intentional whitespace separating command groups and logical sections

## 2. Color Palette & Roles

### Light Theme (Parchment)
- **Gitwise Orange (#E69138)** — Primary accent. Used for the terminal cursor icon, key call-to-action elements, and interactive highlights. The single vibrant color in an otherwise restrained palette.
- **Deep Charcoal (#1A1A1A)** — Primary text and foreground. Used for headings, logo type, and high-priority output. Provides strong readable contrast against the parchment background.
- **Off-White / Parchment (#F8F6F1)** — Primary surface and background. A soft, low-strain base color that reduces eye fatigue during extended CLI sessions. More inviting than pure white.
- **Medium Gray (#666666)** — Secondary text and metadata. Used for labels, descriptions, and supporting information like "GIT UTILITIES • CLI".

### Dark Theme (Terminal)
- **Gitwise Orange (#E69138)** — Primary accent (shared). Command highlights and cursor elements maintain brand consistency across themes.
- **Light Gray (#D1D1D1)** — Primary text. Ensures scannability against the deep matte background.
- **Terminal Black (#121214)** — Primary surface. Deep matte background evoking a modern terminal emulator.
- **Muted Gray (#808080)** — Secondary text. Dimmed terminal output and comments, creating clear visual hierarchy.

### Functional Status Colors
- **Success Green (#4CAF50)** — Completed operations, ready states, positive indicators.
- **Error Red (#F44336)** — Failed operations, validation errors, critical alerts.

### Design Intent
The palette supports dual themes with shared accent identity. Orange remains the sole chromatic anchor in both contexts, ensuring instant brand recognition. Neutral tones shift between warm parchment (light) and cool terminal black (dark) while maintaining high contrast ratios for accessibility.

## 3. Typography Rules

**Primary Font Family:** Geometric monospaced (JetBrains Mono, Fira Code, or similar grotesque mono)

### Hierarchy & Weights
- **Logo / Brand Lockups:** Lowercase, bold weight (700), generous letter-spacing for sub-headers. The distinctive "gitwise" wordmark uses wide tracking to establish brand character.
- **Section Headers (H1/H2):** Bold weight (700), standard monospaced sizing. Used for command group titles and major content sections.
- **Body Text / CLI Output:** Regular weight (400), standard line-height. Monospaced rendering preserves alignment critical for tabular data and code references.
- **Secondary Text / Metadata:** Regular weight (400), Medium Gray color. Recedes visually while remaining legible.

### Spacing Principles
- Generous letter-spacing on logo and sub-headers for brand character
- Standard monospaced tracking for body and output (preserves code alignment)
- Whitespace separates command groups and logical sections (utility-first principle)

## 4. Component Stylings

### Logo Usage
- **Stacked:** Splash screens, centralized branding, error states, onboarding.
- **Horizontal:** Headers, navigation bars, terminal prompts, CLI help output.

### Iconography
- Linear, thick-stroke icons with geometric terminals
- Square brackets `[ ]` used to frame content and interactive elements
- Consistent stroke width across all iconographic elements

### Borders & Corners
- Sharp 90-degree corners exclusively — no border-radius
- Reflects the grid-based, terminal system aesthetic
- Creates a distinctive visual identity separate from rounded UI frameworks

### Interactive Elements
- Gitwise Orange (#E69138) for active/focused states and primary CTAs
- Subtle transitions maintaining the no-nonsense terminal feel
- Bracket-framed selections `[x]` for toggles and multi-select elements

## 5. Layout Principles

### Information Hierarchy
- **Utility First:** Layout mimics well-structured terminal output — most important information at the top, supporting details below
- **High Contrast:** Text easily scannable against background in both light and dark modes
- **Intentional Spacing:** Whitespace separates command groups and logical sections clearly

### Grid & Structure
- Content structured in discrete, logically grouped blocks
- Vertical rhythm follows terminal output conventions (consistent line heights, grouped sections)
- Command output uses monospaced alignment for tabular data readability

### Responsive Considerations
- CLI output optimized for standard terminal widths (80-120 columns)
- Content gracefully truncates or wraps for narrower terminals
- Status indicators and color coding degrade gracefully in non-color contexts

## 6. Design Principles

1. **Utility First** — Information hierarchy mirrors well-structured terminal output. Every element earns its place.
2. **High Contrast** — Text scannable against background in both themes. Accessibility is non-negotiable.
3. **Intentional Spacing** — Whitespace separates command groups and logical sections. Density where it matters, breathing room where it helps.
4. **Zero-Decoration** — No gratuitous shadows, gradients, or ornamentation. Form follows function.
5. **Dual-Theme Identity** — Brand recognition maintained across light and dark contexts through shared accent color and consistent typography.
6. **Terminal-Native** — Sharp corners, monospaced type, and bracket motifs reinforce the CLI identity. The design feels like it belongs in a terminal.
