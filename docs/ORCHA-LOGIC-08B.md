# Orcha Logic 0.8B

## Purpose

Orcha Logic 0.8B is a lightweight local reasoning profile for machines where the 1.7B Quality profile is unnecessarily heavy. It uses the official `qwen3.5:0.8b` backbone and an Orcha-authored behavior recipe.

## Provenance

- Backbone: Qwen3.5 0.8B, Apache-2.0.
- Behavior recipe: independently written for Orcha from publicly documented ideas such as structured prompts, adaptive reasoning effort, disciplined tool use, self-critique/revision and constitutional safety.
- It is not an Anthropic model, does not contain Anthropic weights, and does not claim to reproduce hidden Claude chain-of-thought.
- Community checkpoints claiming proprietary-model reasoning distillation are intentionally not bundled because their training-data provenance is not required for Orcha.

## Runtime defaults

- Download size: about 1.0 GB in the current Ollama package.
- Model context capability: up to 256K tokens upstream.
- Orcha working context: 6K by default to control memory/latency on edge machines.
- Virtual context remains 1M through Orcha retrieval rather than forcing the full native window into RAM.

## Decision loop

`intent -> choose direct/reason/tool -> execute minimum sufficient work -> verify -> concise result`

This profile is optimized for chat, lightweight planning, tool selection and short reasoning loops. Quality remains preferred for harder code/architecture tasks when enough RAM is available.
