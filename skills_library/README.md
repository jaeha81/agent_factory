# Skills Library

Agent skill definitions stored as JSON. Tracked in Git and synced across PCs.

## Adding a New Skill

1. Create a file in `skills_library/skills/` named `<skill_id>.skill.json`
2. The API server loads all `*.skill.json` files on startup

## File Naming

```
skills_library/skills/<skill_id>.skill.json
```

`skill_id` must match the `"skill_id"` field inside the JSON.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `skill_id` | string | Unique identifier (matches filename) |
| `name` | string | Display name |
| `description` | string | What this skill does |
| `prompt` | string | System prompt for the skill |

## Optional Fields

| Field | Type | Default |
|-------|------|---------|
| `category` | string | `"custom"` |
| `version` | string | `"1.0.0"` |
| `dependencies` | string[] | `[]` |
| `cost` | string | `"free"` |
| `inputs_schema` | object | — |
| `outputs_schema` | object | — |

## Example

```json
{
  "skill_id": "example_echo",
  "name": "Echo Skill",
  "description": "Echoes the input back as output.",
  "category": "utility",
  "version": "1.0.0",
  "dependencies": [],
  "cost": "free",
  "prompt": "Return the user's input exactly as received."
}
```

See `skills/example_echo.skill.json` for the full example with schema fields.
