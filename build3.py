#!/usr/bin/env python3

################################################################################
## THIS IS JUST A LARGE LANGUAGE MODEL PORT OF THE ORIGINAL PYTHON2 BUILD SCRIPT
## THIS IS JUST A LARGE LANGUAGE MODEL PORT OF THE ORIGINAL PYTHON2 BUILD SCRIPT
## THIS IS JUST A LARGE LANGUAGE MODEL PORT OF THE ORIGINAL PYTHON2 BUILD SCRIPT
##

import sys
import os
import re
import shutil
import subprocess
import shlex  # Used for safer command string formatting if needed, though not strictly necessary here

################################################################################
## Simple Configuration
##

# Use a color terminal?
use_colors = True

# What compiler to use?
compiler = "g++"
# compiler = "clang++"

# Use C++11/C++0x? (Note: c++0x is old, consider c++11, c++14, c++17, c++20 etc.)
use_cpp_standard = "-std=c++11"  # Or "-std=c++17", etc. Keep None to disable.

# Be verbose ?
use_verbose = "--verbose" in sys.argv

# Clean up after being finished?
use_clean = "--clean" in sys.argv

# Ignore warning
ignore_warnings = "--ignore-warnings" in sys.argv

# Get rid of GPL dependencies
no_gpl = "--no-gpl" in sys.argv

# Show header scanning commands?
show_header_scanning = "--show-header-scanning" in sys.argv

# Commands to add to each file
# Examples: "-D_GLIBCXX_DEBUG", "-msse4a", "-DBE_COMPUTE2_COMPATIBLE"
compiler_settings = ["-O3", "-DNDEBUG"]
if ignore_warnings:
    compiler_settings.append("-w")
else:
    compiler_settings.extend(
        ["-Wall", "-Wextra", "-Wpedantic", "-Wdisabled-optimization"]
    )  # Added more modern warnings

if no_gpl:
    compiler_settings.append("-DNO_GPL")

linker_settings = []

source_extensions = [".cpp", ".cxx", ".cc"]  # Added .cc
header_extensions = [".h", ".hpp", ".hxx"]

################################################################################
## Advanced Configuration
##

if use_cpp_standard:
    compiler_settings.append(use_cpp_standard)
    linker_settings.append(use_cpp_standard)


def make_object_file_name(whole_path):
    """Generates the object file name (e.g., path/to/.file.o) from a source file path."""
    path, file_name = os.path.split(whole_path)
    base_name, extension = os.path.splitext(file_name)
    # Place object files in a dedicated directory for cleanliness (optional but good practice)
    # build_dir = ".build"
    # os.makedirs(os.path.join(build_dir, path), exist_ok=True)
    # return os.path.join(build_dir, path, base_name + ".o")
    # Original behavior: place hidden object file in the source directory
    return os.path.join(path, "." + base_name + ".o")


if use_colors and sys.stdout.isatty():  # Check if stdout is a TTY
    color_command = "\033[92m"
    color_error = "\033[91m"
    color_end = "\033[0m"
else:
    color_command = ""
    color_error = ""
    color_end = ""

################################################################################
## Basic commands and source file information extraction
##


def run_command(
    command,
    capture=True,
    check=True,
    show_command=False,
    encoding="utf-8",
    errors="replace",
):
    """Runs a command using subprocess.run, handling output and errors."""
    if show_command:
        # shlex.join is safer for printing commands that might contain spaces
        print(f"{color_command}{shlex.join(command)}{color_end}")

    try:
        # Using subprocess.run for simplicity
        process = subprocess.run(
            command,
            capture_output=capture,
            text=True,  # text=True decodes automatically
            encoding=encoding,
            errors=errors,
            check=check,
        )  # check=True raises CalledProcessError on failure
        return process.stdout, process.stderr
    except FileNotFoundError:
        print(f"{color_error}Error: Command not found: {command[0]}{color_end}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(
            f"{color_error}Command Failed (Exit Code {e.returncode}):{color_end}\n"
            f"{color_command}{shlex.join(e.cmd)}{color_end}\n"
            f"{color_error}Stderr:{color_end}\n{e.stderr or '<No Stderr>'}"
        )
        sys.exit(1)
    except Exception as e:
        print(
            f"{color_error}An unexpected error occurred while running command:{color_end}\n"
            f"{color_command}{shlex.join(command)}{color_end}\n"
            f"{color_error}Error: {e}{color_end}"
        )
        sys.exit(1)


def find_all_includes(source_file):
    """Finds all included header files using the compiler's preprocessor."""
    command = [compiler, "-E", "-M"] + compiler_settings + [source_file]
    stdout, _ = run_command(command, capture=True, show_command=show_header_scanning)
    # Regex finds sequences of non-whitespace characters
    # Filter out the source/object file name itself (ending in .o:) and backslashes
    includes = [
        item
        for item in re.findall(r"(\S+)", stdout)
        if item != "\\" and not os.path.splitext(item)[1] in source_extensions + [".o:"]
    ]
    return includes


def run_compiler(source_file, object_file, flags):
    """Compiles a single source file into an object file."""
    command = (
        [compiler, "-c"] + compiler_settings + flags + [source_file, "-o", object_file]
    )
    run_command(
        command, capture=False, show_command=True
    )  # Don't capture, just show command and let output go to terminal


def run_linker(object_files, executable_file, flags):
    """Links object files into an executable."""
    command = (
        [compiler] + object_files + ["-o", executable_file] + linker_settings + flags
    )
    run_command(
        command, capture=False, show_command=True
    )  # Don't capture, just show command


def find_flags(code, flag_name):
    """Extracts flags specified in comments like '// flag_name: -flag1 -flag2'."""
    # Use re.escape to safely handle flag_name if it contains regex special chars
    pattern = re.escape(flag_name) + r":?\s*(.*)"
    matches = re.findall(pattern, code)
    # Split each line of flags and flatten the list
    flags = [flag for line in matches for flag in shlex.split(line) if flag]
    return flags


def extract_code_flags(file_name):
    """Reads a source file and extracts compile/link flags from comments."""
    try:
        # Explicitly use utf-8 encoding, common for source code
        with open(file_name, "r", encoding="utf-8") as f:
            code = f.read()
    except IOError as e:
        print(f"{color_error}Error reading file {file_name}: {e}{color_end}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"{color_error}Error decoding file {file_name} as UTF-8: {e}{color_end}")
        print(f"{color_error}Ensure the file is saved with UTF-8 encoding.{color_end}")
        sys.exit(1)

    compile_self_flags = find_flags(code, "compile with")
    compile_related_flags = find_flags(code, "compile related with")
    compile_all_flags = find_flags(code, "compile all with")
    link_flags = find_flags(code, "link with")

    return compile_self_flags, compile_related_flags, compile_all_flags, link_flags


def get_last_modified(file_path):
    """Gets the last modification time of a file, returning 0 if it doesn't exist."""
    try:
        if os.path.exists(file_path):
            return os.path.getmtime(file_path)
        else:
            return 0.0  # Use float for time comparisons
    except OSError:  # Handle potential permission errors etc.
        return 0.0


################################################################################
## Find all source files
##
source_file_list = []
main_file_list = []
header_file_list = []


def gen_file_lists():
    """Walks the current directory and finds source, header, and main files."""
    global source_file_list, main_file_list, header_file_list
    source_file_list = []
    header_file_list = []
    main_files_found = []

    for root, dirs, files in os.walk("."):
        # Simple way to ignore hidden directories (like .git, .build)
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        files = [f for f in files if not f.startswith(".")]

        for file_name in files:
            full_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(full_path, ".")
            _, ext = os.path.splitext(file_name)

            if ext in source_extensions:
                source_file_list.append(rel_path)
                try:
                    # Check for main function and "// do not build" comment
                    # Use encoding='utf-8' and handle potential errors
                    with open(rel_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    # More robust main check (allows different spacing/return types like void)
                    has_main = re.search(r"\bmain\s*\(", content, re.MULTILINE)
                    is_buildable = (
                        re.search(
                            r"//\s+do\s+not\s+build",
                            content,
                            re.IGNORECASE | re.MULTILINE,
                        )
                        is None
                    )

                    if has_main and is_buildable:
                        main_files_found.append(rel_path)
                except IOError:
                    # Ignore files we can't read for main detection
                    if use_verbose:
                        print(
                            f"Warning: Could not read {rel_path} to check for main function."
                        )
                except Exception as e:
                    if use_verbose:
                        print(
                            f"Warning: Error processing {rel_path} for main function: {e}"
                        )

            elif ext in header_extensions:
                header_file_list.append(rel_path)

    # Sort lists for consistent output
    source_file_list.sort()
    header_file_list.sort()
    main_file_list[:] = sorted(main_files_found)  # Update the global list


gen_file_lists()

if use_verbose:
    if not source_file_list:
        print("No source files were found.")
    else:
        print("Found the following source files:")
        print(" * " + "\n * ".join(source_file_list))
    print()

    if not header_file_list:
        print("No header files were found.")
    else:
        print("Found the following header files:")
        print(" * " + "\n * ".join(header_file_list))
    print()

    if not main_file_list:
        print(
            "No source file was identified as a main file (containing 'main()' and not '// do not build')."
        )
    else:
        print("The following source files were identified as main files:")
        print(" * " + "\n * ".join(main_file_list))
    print()

################################################################################
## Generate Dependencies
##

# Using dictionaries for easier lookups
all_header_include = {}  # source_file -> list of all headers included (transitively via compiler)
local_header_include = {}  # source_file -> list of local project headers included
direct_source_depend = {}  # source_file -> list of source files corresponding to local headers
link_against = {}  # source_file -> list of all source files needed for linking (transitive)


def gen_dependencies():
    """Generates dependency information between source and header files."""
    global all_header_include, local_header_include, direct_source_depend, link_against

    header_set = set(header_file_list)  # For faster lookups

    print("Scanning dependencies...")
    for i, src_file in enumerate(source_file_list):
        if use_verbose:
            print(f" [{i + 1}/{len(source_file_list)}] Scanning {src_file}...")
        else:
            # Simple progress indicator
            print(f"\rScanning dependencies... {i + 1}/{len(source_file_list)}", end="")

        all_includes = find_all_includes(src_file)
        # Filter for headers that are part of the project files found earlier
        local_includes = [inc for inc in all_includes if inc in header_set]

        # Find source files corresponding to the local headers included
        # e.g., if "foo.h" is included, look for "foo.cpp", "foo.cxx", etc.
        direct_deps = set()
        for header in local_includes:
            base, _ = os.path.splitext(header)
            for src_ext in source_extensions:
                potential_src = base + src_ext
                if potential_src in source_file_list:
                    direct_deps.add(potential_src)

        all_header_include[src_file] = sorted(all_includes)
        local_header_include[src_file] = sorted(local_includes)
        direct_source_depend[src_file] = sorted(list(direct_deps))

    print()  # Newline after progress indicator

    # Calculate transitive link dependencies (all files needed to link a main file)
    print("Calculating link dependencies...")
    for src_file in source_file_list:
        visited = set()
        unvisited = [src_file]  # Start with the file itself
        while unvisited:
            current_file = unvisited.pop()
            if current_file not in visited:
                visited.add(current_file)
                # Add direct dependencies that haven't been visited or queued
                deps_to_add = [
                    dep
                    for dep in direct_source_depend.get(current_file, [])
                    if dep not in visited and dep not in unvisited
                ]
                unvisited.extend(deps_to_add)
        link_against[src_file] = sorted(list(visited))


gen_dependencies()

if use_verbose:
    print("\nDependency Summary:")
    for x in source_file_list:
        print(f"--- File: {x} ---")
        print(" Local Headers Included:")
        print(f"  * " + "\n  * ".join(local_header_include.get(x, ["None"])))
        print(" Directly Depends on Source Files:")
        print(f"  * " + "\n  * ".join(direct_source_depend.get(x, ["None"])))
        print(" Must Be Linked Against (Transitive):")
        print(f"  * " + "\n  * ".join(link_against.get(x, ["None"])))
        print("-" * (len(x) + 12))
    print()


################################################################################
## Flag magic
##


def auto_detect_link_flags(all_includes_list):
    """Auto-detects common library link flags based on included headers."""
    link_flags = set()
    # Get just the basename of headers (e.g., "math.h", "vector")
    header_basenames = {os.path.basename(h) for h in all_includes_list}

    if "math.h" in header_basenames or "cmath" in header_basenames:
        link_flags.add("-lm")
    if "metis.h" in header_basenames:
        link_flags.add("-lmetis")
    # if "kaffpa_interface.h" in header_basenames: # Assuming this is the header for kaffpa
    #    link_flags.add("-lkaffpa") # Example
    if any(
        h.startswith("CL/") or h == "cl.h" or "opencl" in h.lower()
        for h in header_basenames
    ):
        link_flags.add("-lOpenCL")
    if "omp.h" in header_basenames:
        link_flags.add("-fopenmp")  # Linker also needs fopenmp usually
    if any(
        h in header_basenames
        for h in ["pthread.h", "thread", "future", "mutex", "atomic"]
    ):
        link_flags.add("-lpthread")

    return list(link_flags)


def auto_detect_compile_flags(all_includes_list):
    """Auto-detects common library compile flags based on included headers."""
    compile_flags = set()
    header_basenames = {os.path.basename(h) for h in all_includes_list}

    if "omp.h" in header_basenames:
        compile_flags.add("-fopenmp")

    return list(compile_flags)


# Dictionaries to store flags per source file
compiler_flags = {}
linker_flags = {}


def gen_flags():
    """Generates compiler and linker flags for each source file, combining auto-detected and user-specified flags."""
    global compiler_flags, linker_flags

    print("Generating build flags...")

    # Store flags extracted from code comments
    code_compile_self = {}
    code_compile_related = {}
    code_compile_all = {}
    code_link_all = {}

    # Step 1: Extract flags from comments and auto-detect flags for each file
    for src_file in source_file_list:
        c_self, c_related, c_all, l_all = extract_code_flags(src_file)
        code_compile_self[src_file] = c_self
        code_compile_related[src_file] = c_related
        code_compile_all[src_file] = c_all
        code_link_all[src_file] = l_all

        # Auto-detect flags based on headers *this* file includes
        all_includes = all_header_include.get(src_file, [])
        auto_link = auto_detect_link_flags(all_includes)
        auto_compile = auto_detect_compile_flags(all_includes)

        # Initialize flag lists for the file
        compiler_flags[src_file] = set(c_self + auto_compile)
        linker_flags[src_file] = set(
            l_all + auto_link
        )  # Linker flags primarily apply to the final link stage

    # Step 2: Propagate flags based on dependencies
    for src_file in source_file_list:
        # Add "compile related" flags from self and direct dependencies
        current_related_flags = set(code_compile_related.get(src_file, []))
        for dep in direct_source_depend.get(src_file, []):
            current_related_flags.update(code_compile_related.get(dep, []))
        compiler_flags[src_file].update(current_related_flags)

        # Add "compile all" and "link all" flags from all transitive dependencies
        current_compile_all_flags = set()
        current_link_all_flags = set()
        for linked_file in link_against.get(src_file, []):
            current_compile_all_flags.update(code_compile_all.get(linked_file, []))
            # Also add auto-detected compile flags from dependencies
            current_compile_all_flags.update(
                auto_detect_compile_flags(all_header_include.get(linked_file, []))
            )

            current_link_all_flags.update(code_link_all.get(linked_file, []))
            # Also add auto-detected link flags from dependencies
            current_link_all_flags.update(
                auto_detect_link_flags(all_header_include.get(linked_file, []))
            )

        compiler_flags[src_file].update(current_compile_all_flags)
        linker_flags[src_file].update(
            current_link_all_flags
        )  # Accumulate all necessary link flags

    # Step 3: Finalize flags (convert back to lists)
    for src_file in source_file_list:
        compiler_flags[src_file] = sorted(list(compiler_flags[src_file]))
        # Linker flags really only matter for the main file being linked,
        # but we calculate them based on all dependencies.
        linker_flags[src_file] = sorted(list(linker_flags[src_file]))

    if use_verbose:
        print("\nFlags Summary:")
        for x in source_file_list:
            print(f"--- File: {x} ---")
            print(f" Compile Flags: {' '.join(compiler_flags.get(x, [])) or '<None>'}")
            # Only show linker flags for main files, as they are applied during linking
            if x in main_file_list:
                print(
                    f" Linker Flags:  {' '.join(linker_flags.get(x, [])) or '<None>'}"
                )
            print("-" * (len(x) + 12))
        print()


gen_flags()


################################################################################
## Determine when source files were last modified
##

header_last_modify = {}
source_last_modify = {}  # Stores the latest modification time relevant to recompiling the source


def gen_last_modified():
    """Calculates the effective last modification time for each source file, considering its headers."""
    global header_last_modify, source_last_modify
    print("Checking modification times...")

    # Get modification times for all headers
    for header_file in header_file_list:
        header_last_modify[header_file] = get_last_modified(header_file)

    # Determine the effective modification time for each source file
    script_mtime = get_last_modified(sys.argv[0])  # Consider the build script itself
    for src_file in source_file_list:
        # Start with the source file's own time and the script's time
        latest_mtime = max(get_last_modified(src_file), script_mtime)

        # Consider the modification times of all locally included headers
        for header_file in local_header_include.get(src_file, []):
            latest_mtime = max(latest_mtime, header_last_modify.get(header_file, 0.0))

        source_last_modify[src_file] = latest_mtime


gen_last_modified()


################################################################################
## Build files
##


def build_all_files():
    """Compiles necessary object files and links main files into executables."""
    if not main_file_list:
        print("No main files found to build.")
        return

    built_something = False
    print("Starting build process...")

    for main_file in main_file_list:
        base_name, _ = os.path.splitext(main_file)
        # Place executable in the same dir as the main file's source by default
        exe_file = base_name

        # Get the list of source files needed to link this executable
        files_to_compile = link_against.get(main_file, [])
        if not files_to_compile:
            print(
                f"Warning: No dependencies found for main file {main_file}, cannot build {exe_file}."
            )
            continue

        object_files = [make_object_file_name(src) for src in files_to_compile]

        if use_verbose:
            print(f"\n--- Building Target: {exe_file} ---")
            print(" Required object files:")
            print("  * " + "\n  * ".join(object_files))
            print("-" * (len(exe_file) + 20))

        # Compile necessary object files
        needs_relink = False
        max_object_mtime = 0.0  # Track latest object file time for linking check

        for src_file in files_to_compile:
            object_file = make_object_file_name(src_file)
            object_mtime = get_last_modified(object_file)
            effective_source_mtime = source_last_modify.get(src_file, 0.0)

            # Recompile if object file doesn't exist or is older than the source/headers/script
            if object_mtime < effective_source_mtime:
                if use_verbose:
                    print(f"Compiling {src_file} -> {object_file}")
                else:
                    print(f"Compiling {src_file}")

                # Ensure directory for object file exists (if using a separate build dir)
                # os.makedirs(os.path.dirname(object_file), exist_ok=True)

                run_compiler(src_file, object_file, compiler_flags.get(src_file, []))
                object_mtime = get_last_modified(
                    object_file
                )  # Update mtime after compile
                needs_relink = True
                built_something = True
            else:
                if use_verbose:
                    print(
                        f"Skipping compilation for {src_file} (object file up-to-date)"
                    )

            max_object_mtime = max(max_object_mtime, object_mtime)

        # Link the executable if necessary
        exe_mtime = get_last_modified(exe_file)
        if needs_relink or exe_mtime < max_object_mtime:
            if use_verbose:
                print(f"Linking {exe_file}")
            else:
                # Only print Linking if we didn't just compile everything
                if not needs_relink:
                    print(f"Relinking {exe_file}")
                else:
                    print(f"Linking {exe_file}")

            run_linker(object_files, exe_file, linker_flags.get(main_file, []))
            built_something = True
        else:
            if use_verbose:
                print(f"Skipping linking for {exe_file} (executable up-to-date)")

    if not built_something:
        print("All targets are up-to-date.")


build_all_files()


################################################################################
## Cleanup
##
def do_cleanup():
    """Removes generated object files."""
    print("Cleaning up object files...")
    cleaned_count = 0
    potential_object_files = {make_object_file_name(y) for y in source_file_list}

    for obj_file in potential_object_files:
        if os.path.exists(obj_file):
            try:
                if use_verbose:
                    print(f"Removing {obj_file}")
                os.remove(obj_file)
                cleaned_count += 1
            except OSError as e:
                print(f"{color_error}Error removing file {obj_file}: {e}{color_end}")
    if cleaned_count > 0:
        print(f"Removed {cleaned_count} object file(s).")
    else:
        print("No object files found to remove.")


if use_clean:
    do_cleanup()

print("\nBuild process finished.")
