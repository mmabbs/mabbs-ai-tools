# Path Encoding Reference

Claude Code encodes project paths as directory names in `~/.claude/projects/`.

## Encoding Scheme

Every character that isn't a letter or digit becomes `-`: path separators, spaces, dots, underscores, hyphens, brackets, braces, parentheses, apostrophes, and so on. Letters and digits are kept as-is.

A dotfile segment like `/.claude` therefore shows up as a double hyphen (`--claude`): one hyphen for the `/`, one for the `.`.

**Examples:**

| Original Path | Encoded |
|---------------|---------|
| `/Users/jdoe` | `-Users-jdoe` |
| `/Users/jdoe/.claude` | `-Users-jdoe--claude` |
| `/Users/jdoe/My Project` | `-Users-jdoe-My-Project` |
| `/Users/jdoe/Notes/{Drafts}` | `-Users-jdoe-Notes--Drafts-` |

Encoded names longer than 200 characters are shortened and get a hash appended.

## The Ambiguity Problem

The encoding is **lossy**. These different paths encode identically:

```
/Users/jdoe/foo/bar        → -Users-jdoe-foo-bar
/Users/jdoe/foo bar        → -Users-jdoe-foo-bar
/Users/jdoe/foo-bar        → -Users-jdoe-foo-bar
/Users/jdoe/foo_bar        → -Users-jdoe-foo-bar
/Users/jdoe/foo.bar        → -Users-jdoe-foo-bar
```

There is no way to decode unambiguously without checking the filesystem.

## Decoding Strategy

Both the `chats` and `config` scanners use the shared decoder in `scripts/lib/pathcodec.py` (`resolve_encoded_path`), so they agree on which projects still exist:

1. Start at `/` and split the encoded name on `-`.
2. At each level, list the real entries in the current directory, encode each entry's name the same way Claude Code does, and look for one that matches the next run of tokens.
3. Descend into a match and continue; back up and try a longer run if the rest doesn't resolve.
4. Return the first full path that exists, or nothing if none does.

Because it compares against names that actually exist, it handles any punctuation in folder names. It reports a project as orphaned when:

- The directory was deleted or moved (the genuine orphan case)
- The encoded name was longer than 200 characters and got shortened with a hash, so it can't be matched back to a path

`decode_project_path` in `check-cc-health-chats.py` is a naive display-only decode (every `-` becomes `/`). It is never used to decide whether a path exists.
