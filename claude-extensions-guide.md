# Extending Claude: Tools, MCP, Skills, Subagents, Workflows, Hooks, Plugins

A quick guide to the ways you can extend Claude: what each one is, how they relate, and when to use each.

Primary source: [Extend Claude Code](https://code.claude.com/docs/en/features-overview.md), which is Anthropic's own comparison page. Quoted phrases come from the official docs.

---

## 1. The short version

- **Tools and MCP:** what Claude *can do* (access to systems)
- **Skills and CLAUDE.md:** what Claude *knows* (instructions and context)
- **Hooks:** what *always happens* (run by the harness, not decided by Claude)
- **Subagents and Workflows:** *who does the work* (one helper, or many)
- **Plugins:** how you *package and share* all of the above

---

## 2. What each piece is

| Piece | What it is | Source |
|---|---|---|
| **Tools** | Functions Claude can call. Claude Code has built-in tools (read and edit files, search, run commands, use the web). On the API, you define your own tools. Everything else in this guide is built on tools. | [Tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md) |
| **MCP** | An open standard that connects Claude to outside tools, databases, and APIs, such as Slack, Gmail, Notion, or your own systems. | [MCP](https://code.claude.com/docs/en/mcp.md) |
| **Skill** | A `SKILL.md` file of instructions, with optional scripts and reference files. Only the skill's description is in context until Claude decides the skill is relevant, or you run it with `/name`. | [Skills](https://code.claude.com/docs/en/skills.md) |
| **Slash command** | A prompt you trigger by typing `/name`. Custom commands have been *"merged into skills"*: `.claude/commands/x.md` and `.claude/skills/x/SKILL.md` both create `/x`. | [Commands](https://code.claude.com/docs/en/commands.md) |
| **CLAUDE.md / memory** | *"Persistent context loaded every conversation."* Anthropic describes it as *context, not enforced configuration*. | [Memory](https://code.claude.com/docs/en/memory.md) |
| **Subagent** | A separate Claude that takes on one task in its own context window and returns only the result. | [Subagents](https://code.claude.com/docs/en/sub-agents.md) |
| **Workflow** (Claude Code) | *"A JavaScript script that orchestrates many subagents at once."* The script holds the plan, such as fan out, verify, then merge. | [Workflows](https://code.claude.com/docs/en/workflows.md) |
| **Hook** | A command that the harness runs at lifecycle points (before or after a tool call, on stop, and so on). It gives you *"deterministic control"*. | [Hooks](https://code.claude.com/docs/en/hooks-guide.md) |
| **Plugin** | *"A directory of skills, agents, hooks, MCP servers, or other components that Claude Code installs and loads as one unit."* | [Plugins](https://code.claude.com/docs/en/plugins/overview.md) |

---

## 3. Where plugins fit

A plugin doesn't give Claude any new ability on its own. It's a way to package the other pieces and share them.

```
my-plugin/
├── skills/        → how to do things
├── agents/        → specialized subagents
├── hooks/         → things that always run
├── .mcp.json      → connections to outside systems
└── commands/      → slash commands
```

- Without plugins, you'd copy each skill, hook config, and MCP setting into every person's machine or repo by hand.
- With a plugin, people install it once (usually from a marketplace) and get the whole setup together, versioned.
- The docs say skills, subagents, hooks, and MCP *"all work on their own, without a plugin."* So you don't need a plugin to start. Package things into one when you have something worth sharing.

**Example:** a "small-business" plugin can ship dozens of skills (invoice chasing, payroll prep, and so on) along with the MCP connectors they rely on (QuickBooks, Gmail, Stripe). The team installs it once and has everything.

---

## 4. How deterministic each one is

A common misconception is that skills are the "deterministic" option. They aren't.

```
More flexible  ◄────────────────────────────────────────────►  More deterministic
  CLAUDE.md        Skill            Subagent       Workflow           Hook
  (context)    (instructions    (Claude runs   (code runs the    (code, every
               Claude reads)     a side task)   agents; each       time, no
                                                agent's work is    model choice)
                                                still model
                                                output)
```

- **Skill:** Claude decides *whether* to load it and *how* to follow it. The model holds the plan.
- **Workflow:** the script holds the plan. The structure runs the same way every time; the work inside each step does not.
- **Hook:** fully deterministic. If something must happen with no exceptions, use a hook.

### Skills vs workflows

They work together. Each agent in a workflow can load a skill for *how* to do its step, while the script decides *when and where* each step runs. A skill can also start a workflow once a task gets big enough.

**Rule of thumb:** start with a skill. Move to a workflow when one agent can't hold the whole job, or when the job needs the same structure on every run.

---

## 5. When to use each

| Use… | When… | Don't use it when… |
|---|---|---|
| **Tools** | You're building on the API and Claude needs to *take actions*, not just answer. | Claude Code already has a built-in tool or an MCP server for the job. |
| **MCP** | Claude needs access to a system it can't reach. The docs' cue: *"you find yourself copying data into chat from another tool."* | Claude already has the access, and what it lacks is the right *process*. That's a skill. |
| **Skill** | *"You keep pasting the same instructions, checklist, or multi-step procedure into chat."* | It applies to every conversation (use CLAUDE.md), or it must happen every time (use a hook). |
| **Slash command** | You want to trigger a saved prompt by hand. Write it as a skill now. | Claude should pick it up automatically. Write a skill with a good description instead. |
| **CLAUDE.md** | You have "always do X" project conventions and context that apply to every session. | The instructions are long or only matter sometimes (use a skill), or they must be enforced (use a hook). |
| **Subagent** | *"A side task would flood your main conversation with search results, logs, or file contents you won't reference again."* | The task needs back-and-forth with you. Keep it in the main conversation. |
| **Workflow** | *"A task needs more agents than one conversation can coordinate."* Large jobs that can run in parallel and should run the same way each time. | One agent can handle the job. Workflows cost more, so opt in on purpose. |
| **Hook** | It should happen *"the same way every time and doesn't need Claude to think"*: lint after edits, block dangerous commands, send notifications. | The step needs judgment or context. Use a skill. |
| **Plugin** | You want *"several skills, subagents, hooks, or MCP servers packaged as one unit"* to share with a team or the community. | You only have one skill for yourself. Put it in `.claude/skills/`. |

---

## 6. Decision path

1. Does Claude need access to a new system? Use **MCP**, or **tools** if you're on the API.
2. Does Claude need to know *your process*? Write a **skill**.
3. Should it apply to every session? Put it in **CLAUDE.md**.
4. Must it happen every time, no exceptions? Add a **hook**.
5. Would a side task clutter the conversation? Use a **subagent**.
6. Does the job need many agents running to a set structure? Use a **workflow**.
7. Do you want to share the whole setup? Package it as a **plugin**.

---

## A note on the word "workflow"

The word "workflow" means two different things:

- **Claude Code "dynamic workflow":** the multi-subagent script described above.
- **[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents):** here "workflows" are *"systems where LLMs and tools are orchestrated through predefined code paths,"* in contrast to **agents**, where *"LLMs dynamically direct their own processes and tool usage."* The guidance is to find *"the simplest solution possible, and only [increase] complexity when needed."*

The two ideas are similar (in both, code holds the plan), but no Anthropic doc connects them, so treat them as separate terms.
