#!/usr/bin/env bash
# Prompt: git_repo | git_branch | /current/dir $
# Uses PROMPT_COMMAND so \[ \] escapes work correctly with readline.

__dc_ps1() {
    local repo branch cwd

    repo=$(git rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$repo" ]; then
        repo=$(basename "$repo")
        branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
        branch=${branch:-"(no branch)"}
        cwd=$(pwd | sed "s|^/workspace|~|" | sed "s|^$HOME|~|")

        PS1="\[\e[1;36m\]${repo}\[\e[0m\]"    # cyan repo name
        PS1+=" \[\e[0;90m\]|\[\e[0m\] "
        PS1+="\[\e[1;33m\]${branch}\[\e[0m\]" # yellow branch
        PS1+=" \[\e[0;90m\]|\[\e[0m\] "
        PS1+="\[\e[1;32m\]${cwd}\[\e[0m\]"    # green path
        PS1+=" \[\e[0;90m\]\$\[\e[0m\] "
    else
        cwd=$(pwd | sed "s|^/workspace|~|" | sed "s|^$HOME|~|")
        PS1="\[\e[1;32m\]${cwd}\[\e[0m\] \[\e[0;90m\]\$\[\e[0m\] "
    fi
}

PROMPT_COMMAND='__dc_ps1'
