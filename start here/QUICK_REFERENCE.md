# ⚡ QUICK REFERENCE CARD

## Daily Commands
```bash
# Start chat
python -m identityos chat --identity my_id

# New identity
python -m identityos create --name "my_id" --persona "..."

# List identities
python -m identityos list

# Backup identity
cp -r ~/.identity_store/my_id ~/backups/my_id_$(date +%Y%m%d)
```

## In-Chat Essentials
```
/capability install github browser filesystem command_exec web worldmonitor
/skill github.search_repositories {"query": "topic"}
/skill browser.navigate {"url": "https://..."}
/skill filesystem.write {"path": "file.py", "content": "code"}
/skill command_exec.execute {"command": "python file.py"}
/skill worldmonitor.list_sources {"view": "summary"}
/skill worldmonitor.country_risk {"country_code": "IR"}
```

## Memory Commands
```
/fact add "key info" --tier core|semantic|episodic
/fact list --tier semantic
/skill memory.search {"query": "term", "tier": "semantic", "limit": 10}
/memory
```

## Task Automation
```
/task create "description" --recurring 300      # Every 5 min
/task create "description" --cron "0 8 * * *"   # Daily 8am
/task list
/task cancel <id>
```

## Model Switching
```
/config set adapter ollama|openai|groq|anthropic
/config set model gpt-4o|llama-3.3-70b|phi4-mini:latest
```

## Capability Dev
```
# Generate via chat: "I need a capability that..."
# Test: /skill my_cap.do_thing {"param": "value"}
# Export: /capability export my_cap --output ./caps/
```

## File Locations
```
~/.identity_store/<id>/identity.json      # Identity config
~/.identity_store/<id>/memory/            # All memory tiers
~/.identity_store/<id>/capabilities/      # Installed caps
~/.identity_store/<id>/facts/             # Core/semantic/episodic
~/.identity_store/<id>/goals/             # Active goals
.env                                       # API keys, adapter config
```

## Free WorldMonitor Skills (No Key)
```
worldmonitor.list_sources     worldmonitor.list_tools
worldmonitor.list_prompts     worldmonitor.list_resources
worldmonitor.health_compact   worldmonitor.call_tool
```

## Pro Keys to Add
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-...
WORLDMONITOR_API_KEY=wm_...   # For authenticated skills
```

## Emergency
```
/save                    # Force persist
/reset                   # Soft reset
/exit                    # Quit (auto-save)
Ctrl+C                   # Interrupt current task
```