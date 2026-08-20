# The commit checks: what they're for, how they fail, what to do

These are the checks that run when you `git commit`. This file is written
for whoever is at the keyboard, not for whoever wrote them.

---

## The one-paragraph version

Seven small programs look at what you're about to commit and try to stop
two things: a password going into a public repo readable, and one machine's
private settings overwriting another machine's. They are a safety net, not
a lock — **every single one can be stepped around, on purpose, and every
failure message now tells you how.** If a check ever blocks you and you
can't get past it, that is a bug in the check, not in you. Report it.

---

## The rule they all follow now

> **A check may only stop you over something in the commit you are making
> right now, and it must always tell you a way to proceed.**

Everything else it notices, it mentions and lets you through.

That second half was the missing piece. A check can be completely correct
about a problem and still be useless, if the only fix it names needs a file
or a key you don't have. Then you're just stuck, and the only exit —
`git commit --no-verify` — was never written down anywhere.

### Why not just check everything, always?

That's what they did before, and here's the cost in plain terms: **one
broken thing anywhere in the repo stopped every commit by everybody.** Not
the person who broke it — whoever came next. You hit exactly this. A
one-line typo fix in a text document was refused for days because of an
unrelated settings file, on a machine that had no way to fix it.

The repo-wide checking didn't disappear. It moved to GitHub, which runs the
same programs over everything with their repo-wide switches — `--all` for
the hostvars and hygiene checks, `--repo` for the encoding one. Your laptop checks your change;
GitHub checks the whole repo.

Know when that happens, because it is not "after every push":
`.github/workflows/validate.yml` runs on pushes to `main` and on pull
requests targeting `main`. A topic branch with no pull request open yet gets
no repo-wide run. Secret scanning is the exception and deliberately so --
`.github/workflows/secret-scan.yml` triggers on every branch, because a
credential is exposed the moment it is pushed.

---

## Does this make the boat less secure? No. Here's the honest accounting.

**What still blocks, exactly as before** (verified by running each one):

| The dangerous thing | Still blocked |
|---|---|
| A password typed into a config file in the clear | yes |
| A file that's supposed to be encrypted, going in unencrypted | yes |
| `.env` or the age key getting committed | yes |
| A real email address that should have been anonymised | yes |
| Your machine's private URL overwriting everyone else's | yes |
| Changing the captain passwords you asked us to leave alone | yes |

**What changed:** those checks now fire when *your commit contains the
risky file*, instead of firing on every commit forever once anything
anywhere is off. In every one of those rows, the danger only becomes real
at the moment the file is actually in a commit. Before that moment there's
nothing to catch.

**Two things still block every commit,** and deliberately so. Both are
about a clone that is unsafe, rather than a commit that is:

- **Real secrets sitting readable on this machine, with no way to scramble
  them again.** That is a standing condition, not something you did in this
  commit, and it does not fix itself. Waiting for you to stage one of those
  files means you might find out via `git add .`. A fresh laptop with no
  key never trips this: there the files are still scrambled, so nothing is
  in the clear.
- **A clone that holds secrets but has no scrambling set up.** On a machine
  in strict mode that is the August 2026 incident waiting to happen, so it
  blocks even with nothing risky staged. A contributor clone gets a warning
  instead and can still commit.

**The one thing that is genuinely weaker,** stated plainly rather than
buried: if something bad is *already* in the repo and nobody stages it
again, your laptop won't shout about it on every commit — it mentions it
and moves on. GitHub still catches it after you push. In exchange, you can
work. I think that's the right trade and I'd rather you know it's a trade.

**On making `--no-verify` discoverable:** writing it in the error messages
does not lower the bar. It was always one web search away, and the config
file already said out loud that these hooks are bypassable by design. The
only people the secrecy inconvenienced were the honest ones in a hurry.

---

## How each check fails, and what you do

Every failure message now has the same five parts, in this order:

1. **which check** — so you can skip just that one
2. **which file** — always a real path you can look at
3. **what's actually wrong** — in words, not the rule's name
4. **the command that fixes it** — copy and paste it
5. **what to do if you can't run that command** — the important one

### `hostvars-placeholders` — "your private URL is about to overwrite everyone's"

**What it's for.** One settings file has to say `http://ntfy:80` on the dev
machine and `http://localhost:8090` on the boat. Git stores a blank —
`{{ ntfy_url }}` — and each machine fills it in from a private file called
`hostvars.local.yaml`. This check makes sure the blank, not your filled-in
value, is what goes into git.

**How it fails.** If you don't have `hostvars.local.yaml`, the blank can't
be put back, and your literal value ends up in the commit.

**The trap it used to be.** It told you to run `hostvars_filter.py refresh`.
`refresh` needs `hostvars.local.yaml`. If you don't have that file, you
can't run the fix — and the fix was the only thing it mentioned. A circle
with no exit. **This is the one that cost you days.**

**What happens now.** It only speaks up if the settings file is in *your*
commit. If it is, it says: set the value and run refresh — *and* "no
`hostvars.local.yaml`? Then just take this one file out of the commit:
`git restore --staged <file>`, and everything else goes through."

**If it blocks you:** you almost certainly didn't mean to commit that
settings file. Drop it with `git restore --staged` — your copy on disk is
untouched — and commit the rest.

### `repo-hygiene` — "this clone can't encrypt, and you're committing a secret"

**What it's for.** The repo says certain files must be scrambled before git
sees them. That scrambling only happens if the clone was set up for it. If
it wasn't, those files go in **readable** and nothing says a word. That
happened on the boat Pi in August 2026, in a public repo.

**How it fails.** It notices the scrambling isn't set up.

**The trap it used to be.** It blocked *everything* on any machine that
wasn't set up, and told you to run `setup-git-filters.sh` — which needs
encryption tools and the boat's private key. A fresh laptop has neither. No
exit.

**What happens now.** No secret file in your commit? It says "heads up, this
clone can't encrypt — sort that before you commit one of those files" and
lets you through. Secret file *is* in your commit? It stops you, names the
file, and says: set it up, or take that file out of the commit, and if you
didn't put it there, skip the check and tell whoever did.

Two exceptions, both above under *What changed*: on a machine that already
holds secrets (strict mode) the "heads up" is a block instead, and a
machine with readable secrets it cannot re-scramble is stopped on every
commit until that is sorted. Neither depends on what you staged.

**If it blocks you:** don't force it. That message means a real secret would
go into a public repo readable. Take the file out of the commit.

### `sops-secret-guard` — "that looks like a password"

**What it's for.** The broadest net. It reads the lines you're committing
and looks for anything shaped like a password, token or key, in any config
file — including files nobody ever configured. This is the one that catches
the leak nobody anticipated, and it was already well built.

**How it fails.** It matches a field called `password` / `token` / `apikey`
whose value isn't scrambled. Sometimes that's a false alarm — a test using a
deliberately-wrong password.

**What was wrong with it.** Only the wording. It said "a staged line in a
config file looks like a cleartext credential" — and never told you *which
file*. You'd have to hunt.

**What happens now.** Same detection, unchanged. It names the file, and
offers the exits. It still never prints the secret itself, so the error
message can't become the leak.

**If it blocks you:** read the line it points at. Real secret → encrypt it.
Genuine false alarm → take the file out, or `SKIP=sops-secret-guard`.

### `encoding-health` — "a character got mangled"

**What it's for.** The boat Pi's text settings are subtly wrong, so a script
reading a document there can turn an em dash into garbled characters —
permanently, in a committed file. This spots that damage.

<!-- The line below is a real, deliberate example of the damage. It is why
     this file declares the opt-out marker: encoding-health: allow-mojibake -->

An em dash that has been through it comes out looking like `â€"`. A degree
sign becomes `Â°`. Once that is committed, the original character is gone.

**How it fails.** It finds mangled characters, or a file that isn't valid
text.

**The trap it used to be.** It scanned *every* file in the repo, so one
document damaged months ago blocked every commit forever. And it named **no
fix at all** — it told you something was broken and left you there.

**What happens now.** It only looks at files in your commit. And there's a
real repair command: `check_encoding_health.py --fix <file>`.

**One thing worth knowing about the repair:** it fixes the damaged bits and
leaves genuine special characters alone. My first attempt re-encoded the
whole file, which broke on any document containing a real em dash — i.e.
nearly all of yours. It's tested against exactly that case now. If it isn't
confident, it refuses and tells you how to restore the file from an older
commit rather than guessing and mangling it worse.

---

## The failure I could not fix

**Two Claude sessions sharing one folder.** Git has one "staging area" per
folder. If another session puts a broken file in it, your commit trips over
their work. Narrowing the checks to "your commit" doesn't help, because
their file genuinely is in your commit.

The checks now name the exact file and say: *if you didn't stage this,
another session did — don't undo their work, use `SKIP=<check>` for this
commit and go tell them.* That's damage control, not a cure.

The actual cure is that sessions shouldn't share a folder — which is
already the standing instruction, and this is one more reason it matters.

---

## Other ways these can still go wrong

**They can be wrong about what's in your commit.** All four ask git what
you're committing. If git can't answer, they check *everything* instead of
nothing — a check that goes quiet when confused is worse than one that's
noisy. There are tests for this.

**They can be skipped entirely.** `--no-verify` skips all of them, and a
fresh clone doesn't have them installed until someone runs the setup. This
is by design and always was. GitHub is where the repo-wide checking
actually happens, and unlike the local hooks it can't be switched off from
a laptop — but two limits are worth knowing rather than assuming:

- **A red check on GitHub does not currently block a merge.** `main` has no
  branch protection and no required status checks, so the results are
  information, not a gate. Whether that changes is the owner's call; until
  it does, "CI will catch it" means someone still has to look.
- **The repo-wide checks only run on pull requests and on `main`.** A
  `--no-verify` commit sitting on a topic branch with no PR open has been
  seen only by `prepush-secret-scan`, which runs locally and is itself
  bypassable with `git push --no-verify`. Secret scanning is the exception
  and covers every branch push.

**GitHub could drift out of step.** The checks are now scoped on your laptop
and unscoped on GitHub. If someone edits one side only, the two disagree and
coverage quietly falls through the gap. The GitHub config has a comment
saying so, in the file, next to the commands.

**The password-shaped-text check can cry wolf.** It matches on field *names*.
A checker that raises false alarms gets ignored, and an ignored checker
protects nothing — that's why the messages now say how to allow a genuine
exception rather than leaving `--no-verify` as the only response.

---

## Cheat sheet

| Situation | Do this |
|---|---|
| A check named a file you didn't mean to commit | `git restore --staged <file>` — your copy on disk is safe |
| One check is wrong, the rest are fine | `SKIP=<check-name> git commit ...` |
| Mangled characters in a file you edited | `python3 scripts/check_encoding_health.py --fix <file>` |
| Your private URL got into the commit | `git restore --staged signalk/plugin-config-data/signalk-ntfy.json` |
| Everything's on fire and you need the commit | `git commit --no-verify` — then tell someone |
| A check blocked you with no way out | **That's a bug. Say so.** |
