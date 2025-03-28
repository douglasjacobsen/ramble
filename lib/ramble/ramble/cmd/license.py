# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from datetime import datetime, timezone
import os
import re
from collections import defaultdict

import ramble.paths
from ramble.util.logger import logger
from spack.util.executable import which
import ramble.repository

description = "list and check license headers on files in ramble"
section = "developer"
level = "long"

#: need the git command to check new files
git = which("git")

#: SPDX license id must appear in the first <license_lines> lines of a file
license_lines = 9

#: Ramble's license identifier
apache2_mit_spdx = "(Apache-2.0 OR MIT)"


# List out regex for object files
def _object_file_regex_list():
    prefix = "var/ramble/repos/.*"
    regex_list = []
    for obj_def in ramble.repository.type_definitions.values():
        regex = rf'{prefix}/{obj_def["file_name"]}$'
        regex_list.append(regex)
    return regex_list


#: regular expressions for licensed files.
licensed_files = [
    # ramble scripts
    r"bin/ramble$",
    r"bin/ramble-python$",
    # all of ramble core
    r"lib/ramble/ramble/.*\.py$",
    r"lib/ramble/ramble/.*\.sh$",
    r"lib/ramble/llnl/.*\.py$",
    # rst files in documentation
    r"lib/ramble/docs/(?!command_index|ramble|llnl).*\.rst$",
    r"lib/ramble/docs/.*\.py$",
    # 2 files in external
    r"lib/ramble/external/__init__.py$",
    r"lib/ramble/external/ordereddict_backport.py$",
    # shell scripts in share (include the generated bash completion file)
    r"share/ramble/.*\.sh$",
    r"share/ramble/.*\.bash$",
    r"share/ramble/.*\.csh$",
    r"share/ramble/qa/run-[^/]*$",
    r"share/ramble/bash/.*$",
    r"share/ramble/cloud-build/.*\.yaml$",
    # examples
    r"examples/.*\.yaml$",
] + _object_file_regex_list()


#: licensed files that can have LGPL language in them
#: so far, just this command -- so it can find LGPL things elsewhere
lgpl_exceptions = [
    r"lib/ramble/ramble/cmd/license.py",
    r"lib/ramble/ramble/test/cmd/license.py",
]


def _get_modified_files(root):
    """Get a list of modified files in the current repository."""
    diff_args = ["-C", root, "diff", "HEAD", "--name-only"]
    files = git(*diff_args, output=str).split()
    return files


def _all_ramble_files(root=ramble.paths.prefix, modified_only=False):
    """Generates root-relative paths of all files in the ramble repository."""
    if modified_only:
        yield from _get_modified_files(root)
    else:
        visited = set()
        for cur_root, _, files in os.walk(root):
            for filename in files:
                path = os.path.realpath(os.path.join(cur_root, filename))

                if path not in visited:
                    yield os.path.relpath(path, root)
                    visited.add(path)


def _licensed_files(root=ramble.paths.prefix, modified_only=False):
    for relpath in _all_ramble_files(root, modified_only=modified_only):
        if any(regex.match(relpath) for regex in licensed_files):
            yield relpath


def list_files(args):
    """list files in ramble that should have license headers"""
    for relpath in sorted(_licensed_files()):
        print(os.path.join(ramble.paths.ramble_root, relpath))


# Error codes for license verification. All values are chosen such that
# bool(value) evaluates to True
OLD_LICENSE, SPDX_MISMATCH, GENERAL_MISMATCH = range(1, 4)


class LicenseError:
    def __init__(self):
        self.error_counts = defaultdict(int)

    def add_error(self, error):
        self.error_counts[error] += 1

    def has_errors(self):
        return sum(self.error_counts.values()) > 0

    def error_messages(self):
        total = sum(self.error_counts.values())
        missing = self.error_counts[GENERAL_MISMATCH]
        spdx_mismatch = self.error_counts[SPDX_MISMATCH]
        old_license = self.error_counts[OLD_LICENSE]
        return (
            "%d improperly licensed files" % (total),
            "files with wrong SPDX-License-Identifier:   %d" % spdx_mismatch,
            "files with old license header:              %d" % old_license,
            "files not containing expected license:      %d" % missing,
        )


strict_date_range = f"2022-{datetime.now(timezone.utc).year}"

strict_copyright_date = f"Copyright {strict_date_range}"


def _check_license(lines, path):
    # The years are hard-coded in the license header to allow them to be out-dated.
    # The `strict_copyright_date` below issues warnings as reminders for refreshing.
    license_lines = [
        r"Copyright 2022-2025 The Ramble Authors",
        r"Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or",
        r"https://www.apache.org/licenses/LICENSE-2.0> or the MIT license",
        r"<LICENSE-MIT or https://opensource.org/licenses/MIT>, at your",
        r"option. This file may not be copied, modified, or distributed",
        r"except according to those terms.",
    ]

    found = []

    for line in lines:
        line = re.sub(r"^[\s#\.]*", "", line)
        line = line.rstrip()
        for i, license_line in enumerate(license_lines):
            if re.match(license_line, line):
                # The first line of the license contains the copyright date.
                # We allow it to be out of date but print a warning if it is
                # out of date.
                if i == 0:
                    if not re.search(strict_copyright_date, line):
                        logger.warn(f"{path}: copyright date mismatch")
                found.append(i)

    if len(found) == len(license_lines) and found == list(sorted(found)):
        return

    def old_license(line, path):
        if re.search("This program is free software", line):
            print(f"{path}: has old LGPL license header")
            return OLD_LICENSE

    # If the SPDX identifier is present, then there is a mismatch (since it
    # did not match the above regex)
    def wrong_spdx_identifier(line, path):
        m = re.search(r"SPDX-License-Identifier: ([^\n]*)", line)
        if m and m.group(1) != apache2_mit_spdx:
            print(
                "{}: SPDX license identifier mismatch"
                "(expecting {}, found {})".format(path, apache2_mit_spdx, m.group(1))
            )
            return SPDX_MISMATCH

    checks = [old_license, wrong_spdx_identifier]

    for line in lines:
        for check in checks:
            error = check(line, path)
            if error:
                return error

    print(f"{path}: the license does not match the expected format")
    return GENERAL_MISMATCH


def verify(args):
    """verify that files in ramble have the right license header"""

    license_errors = LicenseError()

    for relpath in _licensed_files(args.root, modified_only=args.modified):
        path = os.path.join(args.root, relpath)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            lines = [line for line in f][:license_lines]

        error = _check_license(lines, path)
        if error:
            license_errors.add_error(error)

    if license_errors.has_errors():
        logger.die(*license_errors.error_messages())
    else:
        logger.msg("No license issues found.")


def update_copyright_year(args):
    """update copyright header for the current year (utc-based) in all licensed files"""
    patt = re.compile(r"Copyright \d{4}-\d{4}")
    for filename in _licensed_files():
        with open(filename) as lic_f:
            lines = lic_f.readlines()
            for i, license_line in enumerate(lines[:license_lines]):
                if patt.search(license_line):
                    lines[i] = patt.sub(strict_copyright_date, license_line)
                    break
        with open(filename, "w") as lic_f:
            lic_f.writelines(lines)

    def replace_text(file, regex, new_text):
        with open(file) as f:
            content = f.read()
            content = re.sub(regex, new_text, content)
        with open(file, "w") as f:
            f.write(content)

    # Update also the licenses and sphinx config file
    replace_text(
        os.path.join(ramble.paths.ramble_root, "LICENSE-MIT"),
        r"Copyright \(c\) \d{4}-\d{4}",
        f"Copyright (c) {strict_date_range}",
    )
    replace_text(
        os.path.join(ramble.paths.ramble_root, "LICENSE-APACHE"),
        r"Copyright \d{4}-\d{4}",
        f"Copyright {strict_date_range}",
    )
    replace_text(
        os.path.join(ramble.paths.ramble_root, "lib", "ramble", "docs", "conf.py"),
        r"\d{4}-\d{4}, Google LLC",
        f"{strict_date_range}, Google LLC",
    )


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="license_command")
    sp.add_parser("list-files", help=list_files.__doc__, description=list_files.__doc__)

    verify_parser = sp.add_parser("verify", help=verify.__doc__, description=verify.__doc__)
    verify_parser.add_argument(
        "--root",
        action="store",
        default=ramble.paths.prefix,
        help="scan a different prefix for license issues",
    )
    verify_parser.add_argument(
        "--modified",
        "-m",
        action="store_true",
        default=False,
        help="verify only the modified files as outputted by `git ls-files --modified`",
    )

    sp.add_parser(
        "update-copyright-year",
        help=update_copyright_year.__doc__,
        description=update_copyright_year.__doc__,
    )


def license(parser, args):
    if not git:
        logger.die("ramble license requires git in your environment")

    licensed_files[:] = [re.compile(regex) for regex in licensed_files]

    commands = {
        "list-files": list_files,
        "verify": verify,
        "update-copyright-year": update_copyright_year,
    }
    return commands[args.license_command](args)
