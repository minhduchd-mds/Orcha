# Orcha UI Contract

This contract is mandatory for product-facing frontend work.

## Source priority

1. User brief / explicit product requirement.
2. Existing Orcha visual baseline inherited from the original Orcha-era `studio/styles.css`.
3. Existing component and interaction patterns.
4. Anthropic Claude Code `frontend-design` quality principles.
5. New experimentation only when it does not conflict with 1–4.

There is no separate official `Orcha Style Rule` file in this repository. The Orcha-derived baseline is the actual visual language already encoded in `studio/styles.css`; Orcha preserves that language instead of inventing a replacement theme.

Claude frontend-design is a quality reference, not a theme. It may improve hierarchy, typography treatment, structure, copy, restraint, responsive behavior, keyboard focus and self-critique, but it must not silently replace Orcha's palette, radius, density, layout or icon language.

## Visual baseline

Canonical tokens originate in `studio/styles.css`:

- canvas `--bg: #191817`
- panel `--panel: #201f1d`
- raised panel `--panel2: #262522`
- sidebar `--side: #171615`
- border `--line: #34322f`
- stronger border `--line2: #423f3a`
- primary text `--text: #f1eee9`
- muted text `--muted: #aaa49c`
- faint text `--faint: #77716a`
- primary accent `--accent: #c87858`
- secondary accent/focus `--accent2: #d89a78`
- success `--green: #79b88d`
- warning `--amber: #d4a45e`
- danger `--red: #d9786e`

`ui-foundation.css` must alias these values rather than create a second palette.

Typography baseline:

`Inter, "Segoe UI", system-ui, -apple-system, sans-serif`

Radius language: compact to medium, generally 8–18px. Do not introduce an unrelated zero-radius editorial system or oversized pill/card language without an explicit brief.

## Icon contract

All product icons are outline SVG.

Required defaults:

```text
viewBox: 0 0 24 24
fill: none
stroke: currentColor
stroke-width: 1.8
stroke-linecap: round
stroke-linejoin: round
```

Rules:

- no new emoji/Unicode glyphs as product icons;
- one visual weight across navigation, toolbar, dialog and Inspector;
- icon-only buttons require `aria-label` plus title/tooltip;
- destructive icons remain outline and use semantic danger color;
- do not mix filled and outline variants in one action family.

The runtime registry lives in `studio/ui-foundation.js`.

## Brand and chat copy

Product-facing name is **Orcha**.

`Orcha`, `Orcha`, and `Orcha` may only remain in explicitly historical or compatibility contexts such as legacy model IDs, migration environment variables, old release notes or compatibility launchers. They must not appear in:

- welcome/chat text;
- assistant metadata;
- permission copy;
- product title/brand;
- dialog labels;
- toast/error/empty states;
- new product-facing UI.

Copy uses plain active language from the user's side of the screen. A control name stays consistent through the full interaction.

## Interaction rules

- No product flow may use browser-native `prompt()`/`alert()` as the final UX.
- Secondary panels need a close/reopen path when appropriate.
- Keyboard focus must be visible.
- Reduced-motion preference must be respected.
- Async UI must represent loading/error/empty/success where relevant.
- Responsive layout preserves information hierarchy and task priority; it is not merely a scaled desktop layout.

## Claude frontend-design adaptation

Use the following Claude principles when they improve Orcha without changing the baseline:

- design choices must be grounded in the actual product/task;
- structure communicates information, not decoration;
- typography and spacing should be deliberate;
- use one meaningful signature idea rather than scattered decoration;
- motion is purposeful and restrained;
- build, critique, remove unnecessary detail, then verify again;
- copy is part of the interface and should be concrete, consistent and useful.

If a Claude-inspired idea would make Orcha look like a different product, reject that idea.

## Frontend completion gate

Before merging UI work:

1. Run `orcha-frontend-design`.
2. Verify outline-icon rule.
3. Verify no retired product name appears in product-facing studio source.
4. Verify focus/reduced-motion/responsive behavior.
5. Run `ux-audit` for experience review when the task changes flows.
6. Run `code-review` for implementation/regression review.
7. Run `python scripts/verify.py`.
