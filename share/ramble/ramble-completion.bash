# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# NOTE: ramble-completion.bash is auto-generated by:
#
#   $ ramble commands --update-completion
#
# Please do not manually modify this file.


# The following global variables are set by Bash programmable completion:
#
#     COMP_CWORD:      An index into ${COMP_WORDS} of the word containing the
#                      current cursor position
#     COMP_KEY:        The key (or final key of a key sequence) used to invoke
#                      the current completion function
#     COMP_LINE:       The current command line
#     COMP_POINT:      The index of the current cursor position relative to the
#                      beginning of the current command
#     COMP_TYPE:       Set to an integer value corresponding to the type of
#                      completion attempted that caused a completion function
#                      to be called
#     COMP_WORDBREAKS: The set of characters that the readline library treats
#                      as word separators when performing word completion
#     COMP_WORDS:      An array variable consisting of the individual words in
#                      the current command line
#
# The following global variable is used by Bash programmable completion:
#
#     COMPREPLY:       An array variable from which bash reads the possible
#                      completions generated by a shell function invoked by the
#                      programmable completion facility
#
# See `man bash` for more details.

# Bash programmable completion for Ramble
_bash_completion_ramble() {
    # In all following examples, let the cursor be denoted by brackets, i.e. []

    # For our purposes, flags should not affect tab completion. For instance,
    # `ramble install []` and `ramble -d install --jobs 8 []` should both give the same
    # possible completions. Therefore, we need to ignore any flags in COMP_WORDS.
    local COMP_WORDS_NO_FLAGS=()
    local index=0
    while [[ "$index" -lt "$COMP_CWORD" ]]
    do
        if [[ "${COMP_WORDS[$index]}" == [a-z]* ]]
        then
            COMP_WORDS_NO_FLAGS+=("${COMP_WORDS[$index]}")
        fi
        let index++
    done

    # Options will be listed by a subfunction named after non-flag arguments.
    # For example, `ramble -d install []` will call _ramble_install
    # and `ramble compiler add []` will call _ramble_compiler_add
    local subfunction=$(IFS='_'; echo "_${COMP_WORDS_NO_FLAGS[*]}")

    # Translate dashes to underscores, as dashes are not permitted in
    # compatibility mode. See https://github.com/ramble/ramble/pull/4079
    subfunction=${subfunction//-/_}

    # However, the word containing the current cursor position needs to be
    # added regardless of whether or not it is a flag. This allows us to
    # complete something like `ramble install --keep-st[]`
    COMP_WORDS_NO_FLAGS+=("${COMP_WORDS[$COMP_CWORD]}")

    # Since we have removed all words after COMP_CWORD, we can safely assume
    # that COMP_CWORD_NO_FLAGS is simply the index of the last element
    local COMP_CWORD_NO_FLAGS=$((${#COMP_WORDS_NO_FLAGS[@]} - 1))

    # There is no guarantee that the cursor is at the end of the command line
    # when tab completion is invoked. For example, in the following situation:
    #     `ramble -d [] install`
    # if the user presses the TAB key, a list of valid flags should be listed.
    # Note that we cannot simply ignore everything after the cursor. In the
    # previous scenario, the user should expect to see a list of flags, but
    # not of other subcommands. Obviously, `ramble -d list install` would be
    # invalid syntax. To accomplish this, we use the variable list_options
    # which is true if the current word starts with '-' or if the cursor is
    # not at the end of the line.
    local list_options=false
    if [[ "${COMP_WORDS[$COMP_CWORD]}" == -* || "$COMP_POINT" -ne "${#COMP_LINE}" ]]
    then
        list_options=true
    fi

    # In general, when evoking tab completion, the user is not expecting to
    # see optional flags mixed in with subcommands or package names. Tab
    # completion is used by those who are either lazy or just bad at spelling.
    # If someone doesn't remember what flag to use, seeing single letter flags
    # in their results won't help them, and they should instead consult the
    # documentation. However, if the user explicitly declares that they are
    # looking for a flag, we can certainly help them out.
    #     `ramble install -[]`
    # and
    #     `ramble install --[]`
    # should list all flags and long flags, respectively. Furthermore, if a
    # subcommand has no non-flag completions, such as `ramble arch []`, it
    # should list flag completions.

    local cur=${COMP_WORDS_NO_FLAGS[$COMP_CWORD_NO_FLAGS]}

    # If the cursor is in the middle of the line, like:
    #     `ramble -d [] install`
    # COMP_WORDS will not contain the empty character, so we have to add it.
    if [[ "${COMP_LINE:$COMP_POINT:1}" == " " ]]
    then
        cur=""
    fi

    # Uncomment this line to enable logging
    #_test_vars >> temp

    # Make sure function exists before calling it
    if [[ "$(type -t $subfunction)" == "function" ]]
    then
        $subfunction
        COMPREPLY=($(compgen -W "$RAMBLE_COMPREPLY" -- "$cur"))
    fi
}

# Helper functions for subcommands
# Results of each query are cached via environment variables

_subcommands() {
    if [[ -z "${RAMBLE_SUBCOMMANDS:-}" ]]
    then
        RAMBLE_SUBCOMMANDS="$(ramble commands)"
    fi
    RAMBLE_COMPREPLY="$RAMBLE_SUBCOMMANDS"
}

_all_applications() {
    if [[ -z "${RAMBLE_ALL_APPLICATIONS:-}" ]]
    then
        RAMBLE_ALL_APPLICATIONS="$(ramble list)"
    fi
    RAMBLE_COMPREPLY="$RAMBLE_ALL_APPLICATIONS"
}

_repos() {
    if [[ -z "${RAMBLE_REPOS:-}" ]]
    then
        RAMBLE_REPOS="$(ramble repo list | awk '{print $1}')"
    fi
    RAMBLE_COMPREPLY="$RAMBLE_REPOS"
}

_workspaces() {
    if [[ -z "${RAMBLE_WORKSPACES:-}" ]]
    then
        RAMBLE_WORKSPACES="$(ramble workspace list)"
    fi
    RAMBLE_COMPREPLY="$RAMBLE_WORKSPACES"
}

_tests() {
    if [[ -z "${RAMBLE_TESTS:-}" ]]
    then
        RAMBLE_TESTS="$(ramble test -l)"
    fi
    RAMBLE_COMPREPLY="$RAMBLE_TESTS"
}

_config_sections() {
    if [[ -z "${RAMBLE_CONFIG_SECTIONS:-}" ]]
    then
        RAMBLE_CONFIG_SECTIONS="$(ramble config list)"
    fi
    RAMBLE_COMPREPLY="$RAMBLE_CONFIG_SECTIONS"
}

_extensions() {
    if [[ -z "${RAMBLE_EXTENSIONS:-}" ]]
    then
        RAMBLE_EXTENSIONS="$(ramble extensions)"
    fi
    RAMBLE_COMPREPLY="$RAMBLE_EXTENSIONS"
}

# Testing functions

# Function for unit testing tab completion
# Syntax: _ramble_completions ramble install py-
_ramble_completions() {
    local COMP_CWORD COMP_KEY COMP_LINE COMP_POINT COMP_TYPE COMP_WORDS COMPREPLY

    # Set each variable the way bash would
    COMP_LINE="$*"
    COMP_POINT=${#COMP_LINE}
    COMP_WORDS=("$@")
    if [[ ${COMP_LINE: -1} == ' ' ]]
    then
        COMP_WORDS+=('')
    fi
    COMP_CWORD=$((${#COMP_WORDS[@]} - 1))
    COMP_KEY=9    # ASCII 09: Horizontal Tab
    COMP_TYPE=64  # ASCII 64: '@', to list completions if the word is not unmodified

    # Run Ramble's tab completion function
    _bash_completion_ramble

    # Return the result
    echo "${COMPREPLY[@]:-}"
}

# Log the environment variables used
# Syntax: _test_vars >> temp
_test_vars() {
    echo "-----------------------------------------------------"
    echo "Variables set by bash:"
    echo
    echo "COMP_LINE:                '$COMP_LINE'"
    echo "# COMP_LINE:              '${#COMP_LINE}'"
    echo "COMP_WORDS:               $(_pretty_print COMP_WORDS[@])"
    echo "# COMP_WORDS:             '${#COMP_WORDS[@]}'"
    echo "COMP_CWORD:               '$COMP_CWORD'"
    echo "COMP_KEY:                 '$COMP_KEY'"
    echo "COMP_POINT:               '$COMP_POINT'"
    echo "COMP_TYPE:                '$COMP_TYPE'"
    echo "COMP_WORDBREAKS:          '$COMP_WORDBREAKS'"
    echo
    echo "Intermediate variables:"
    echo
    echo "COMP_WORDS_NO_FLAGS:      $(_pretty_print COMP_WORDS_NO_FLAGS[@])"
    echo "# COMP_WORDS_NO_FLAGS:    '${#COMP_WORDS_NO_FLAGS[@]}'"
    echo "COMP_CWORD_NO_FLAGS:      '$COMP_CWORD_NO_FLAGS'"
    echo
    echo "Subfunction:              '$subfunction'"
    if $list_options
    then
        echo "List options:             'True'"
    else
        echo "List options:             'False'"
    fi
    echo "Current word:             '$cur'"
}

# Pretty-prints one or more arrays
# Syntax: _pretty_print array1[@] ...
_pretty_print() {
    for arg in $@
    do
        local array=("${!arg}")
        printf "$arg: ["
        printf   "'%s'" "${array[0]}"
        printf ", '%s'" "${array[@]:1}"
        echo "]"
    done
}

complete -o bashdefault -o default -F _bash_completion_ramble ramble

# Ramble commands
#
# Everything below here is auto-generated.

_ramble() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -H --all-help --color -c --config -C --config-scope -d --debug --disable-passthrough -N --disable-logger -P --disable-progress-bar --timestamp --pdb -w --workspace -D --workspace-dir -W --no-workspace --use-workspace-repo -k --insecure -l --enable-locks -L --disable-locks -m --mock --mock-applications --mock-modifiers --mock-package-managers --mock-workflow-managers --mock-base-applications --mock-base-modifiers --mock-base-package-managers --mock-base-workflow-managers -p --profile --sorted-profile --lines -v --verbose --stacktrace -V --version --print-shell-vars"
    else
        RAMBLE_COMPREPLY="attributes clean commands config debug deployment docs edit flake8 help info license list mirror mods on python repo results software-definitions style unit-test workspace"
    fi
}

_ramble_attributes() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --defined --undefined -a --all --by-attribute --applications --modifiers --package_managers --workflow_managers --base_applications --base_modifiers --base_package_managers --base_workflow_managers --maintainers --tags"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_clean() {
    RAMBLE_COMPREPLY="-h --help -d --downloads -m --misc-cache -p --python-cache -r --reports -a --all"
}

_ramble_commands() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --update-completion -a --aliases --format --header --update"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_config() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --scope"
    else
        RAMBLE_COMPREPLY="get blame edit list add remove rm update revert"
    fi
}

_ramble_config_get() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        _config_sections
    fi
}

_ramble_config_blame() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        _config_sections
    fi
}

_ramble_config_edit() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --print-file"
    else
        _config_sections
    fi
}

_ramble_config_list() {
    RAMBLE_COMPREPLY="-h --help"
}

_ramble_config_add() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -f --file"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_config_remove() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_config_rm() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_config_update() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -y --yes-to-all"
    else
        _config_sections
    fi
}

_ramble_config_revert() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -y --yes-to-all"
    else
        _config_sections
    fi
}

_ramble_debug() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMPREPLY="report"
    fi
}

_ramble_debug_report() {
    RAMBLE_COMPREPLY="-h --help"
}

_ramble_deployment() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMPREPLY="push pull"
    fi
}

_ramble_deployment_push() {
    RAMBLE_COMPREPLY="-h --help --tar-archive -t --deployment-name -d --upload-url -u --phases --include-phase-dependencies --where --exclude-where --filter-tags"
}

_ramble_deployment_pull() {
    RAMBLE_COMPREPLY="-h --help --deployment-path -p"
}

_ramble_docs() {
    RAMBLE_COMPREPLY="-h --help"
}

_ramble_edit() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --type -c --command -d --docs -t --test -m --module -r --repo -N --namespace"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_flake8() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -b --base -k --keep-temp -a --all -o --output -r --root-relative -U --no-untracked"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_help() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -a --all --spec"
    else
        _subcommands
    fi
}

_ramble_info() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --type --format --pattern -p --overview -o --verbose -v --all --attributes --attrs"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_license() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMPREPLY="list-files verify update-copyright-year"
    fi
}

_ramble_license_list_files() {
    RAMBLE_COMPREPLY="-h --help"
}

_ramble_license_verify() {
    RAMBLE_COMPREPLY="-h --help --root --modified -m"
}

_ramble_license_update_copyright_year() {
    RAMBLE_COMPREPLY="-h --help"
}

_ramble_list() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -d --search-description --format --update -t --tags --type"
    else
        _all_applications
    fi
}

_ramble_mirror() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -n --no-checksum"
    else
        RAMBLE_COMPREPLY="destroy add remove rm set-url list"
    fi
}

_ramble_mirror_destroy() {
    RAMBLE_COMPREPLY="-h --help -m --mirror-name -u --mirror-url"
}

_ramble_mirror_add() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --scope"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_mirror_remove() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --scope"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_mirror_rm() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --scope"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_mirror_set_url() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --push --scope"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_mirror_list() {
    RAMBLE_COMPREPLY="-h --help --scope"
}

_ramble_mods() {
    RAMBLE_COMPREPLY="-h --help"
}

_ramble_on() {
    RAMBLE_COMPREPLY="-h --help --executor --enable-per-experiment-prints --suppress-run-header --where --exclude-where --filter-tags"
}

_ramble_python() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -V --version -c -u -i -m --path"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_repo() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMPREPLY="create list add remove rm"
    fi
}

_ramble_repo_create() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -d --subdirectory -t --type"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_repo_list() {
    RAMBLE_COMPREPLY="-h --help --scope -t --type"
}

_ramble_repo_add() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --scope -t --type"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_repo_remove() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --scope -t --type"
    else
        _repos
    fi
}

_ramble_repo_rm() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --scope -t --type"
    else
        _repos
    fi
}

_ramble_results() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMPREPLY="upload report"
    fi
}

_ramble_results_upload() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_results_report() {
    RAMBLE_COMPREPLY="-h --help --workspace --strong-scaling --weak-scaling --multi-line --compare --foms --pandas-where -n --normalize --logx --logy --split-by -f --file"
}

_ramble_software_definitions() {
    RAMBLE_COMPREPLY="-h --help -s --summary -c --conflicts -e --error-on-conflict"
}

_ramble_style() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -b --base -a --all -o --output -r --root-relative -U --no-untracked -f --fix -k --keep-temp -t --tool -s --skip"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_unit_test() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -H --pytest-help -l --list -L --list-long -N --list-names -s -k --showlocals"
    else
        _tests
    fi
}

_ramble_workspace() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMPREPLY="activate archive deactivate create concretize setup analyze push-to-cache info edit mirror experiment-logs list ls remove rm generate-config manage"
    fi
}

_ramble_workspace_activate() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --sh --csh --fish --bat -p --prompt --temp -d --dir"
    else
        _workspaces
    fi
}

_ramble_workspace_archive() {
    RAMBLE_COMPREPLY="-h --help --tar-archive -t --prefix -p --upload-url -u --include-secrets --phases --include-phase-dependencies --where --exclude-where"
}

_ramble_workspace_deactivate() {
    RAMBLE_COMPREPLY="-h --help --sh --csh --fish --bat"
}

_ramble_workspace_create() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -c --config -t --template_execute -d --dir --software-dir --inputs-dir -a --activate"
    else
        RAMBLE_COMREPLY=""
    fi
}

_ramble_workspace_concretize() {
    RAMBLE_COMPREPLY="-h --help -f --force-concretize --simplify --quiet -q"
}

_ramble_workspace_setup() {
    RAMBLE_COMPREPLY="-h --help --dry-run --phases --include-phase-dependencies --where --exclude-where --filter-tags"
}

_ramble_workspace_analyze() {
    RAMBLE_COMPREPLY="-h --help -f --formats -u --upload -p --print-results -s --summary-only --phases --include-phase-dependencies --where --exclude-where --filter-tags"
}

_ramble_workspace_push_to_cache() {
    RAMBLE_COMPREPLY="-h --help -d --where --exclude-where --filter-tags"
}

_ramble_workspace_info() {
    RAMBLE_COMPREPLY="-h --help --software --all-software --templates --expansions --tags --phases --where --exclude-where --filter-tags -v --verbose"
}

_ramble_workspace_edit() {
    RAMBLE_COMPREPLY="-h --help -f --file -c --config_only -t --template_only -l --license_only --all -p --print-file"
}

_ramble_workspace_mirror() {
    RAMBLE_COMPREPLY="-h --help -d --dry-run --phases --include-phase-dependencies --where --exclude-where"
}

_ramble_workspace_experiment_logs() {
    RAMBLE_COMPREPLY="-h --help --limit-one --first-failed --failed --where --exclude-where --filter-tags"
}

_ramble_workspace_list() {
    RAMBLE_COMPREPLY="-h --help"
}

_ramble_workspace_ls() {
    RAMBLE_COMPREPLY="-h --help"
}

_ramble_workspace_remove() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -y --yes-to-all"
    else
        _workspaces
    fi
}

_ramble_workspace_rm() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help -y --yes-to-all"
    else
        _workspaces
    fi
}

_ramble_workspace_generate_config() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --workload-filter --wf --variable-filter --vf --variable-definition -v --experiment-name -e --package-manager -p --dry-run --print --overwrite --include-default-variables -i --workload-name-variable -w --zip -z --matrix -m"
    else
        _all_applications
    fi
}

_ramble_workspace_manage() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help"
    else
        RAMBLE_COMPREPLY="experiments software includes"
    fi
}

_ramble_workspace_manage_experiments() {
    if $list_options
    then
        RAMBLE_COMPREPLY="-h --help --workload-filter --wf --variable-filter --vf --variable-definition -v --experiment-name -e --package-manager -p --dry-run --print --overwrite --include-default-variables -i --workload-name-variable -w --zip -z --matrix -m"
    else
        _all_applications
    fi
}

_ramble_workspace_manage_software() {
    RAMBLE_COMPREPLY="-h --help --environment-name --env --environment-packages --external-env --package-name --pkg --package-spec --pkg-spec --spec --compiler-package --compiler-pkg --compiler --compiler-spec --package-manager-prefix --prefix --remove --delete --overwrite -o --dry-run --print"
}

_ramble_workspace_manage_includes() {
    RAMBLE_COMPREPLY="-h --help --list -l --remove -r --remove-index --add -a"
}
