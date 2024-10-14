#!/usr/bin/env python3

import os
import argparse
import subprocess
import json
import sys

def get_shell_env(image_name):
    try:
        # Run the podman inspect command
        result = subprocess.run(['podman', 'inspect', image_name], stdout=subprocess.PIPE, check=True)
        # Load the output into JSON format
        inspect_data = json.loads(result.stdout)
        
        # Find environment variables
        env_variables = []
        if inspect_data and 'Config' in inspect_data[0] and 'Env' in inspect_data[0]['Config']:
            env_variables = inspect_data[0]['Config']['Env']
        
        # Find the SHELL variable
        for var in env_variables:
            key, value = var.split('=', 1)
            if key == "SHELL":
                return value
        
        # If SHELL variable is not found
        return None

    except subprocess.CalledProcessError as e:
        print(f"Error running podman inspect: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None

def is_valid_basename(base_name):
    """Validates if the base name is allowed based on container image naming rules."""
    # Ensure the base_name is between 1 and 128 characters
    if not (1 <= len(base_name) <= 128):
        return False
    
    # Ensure each character is either lowercase letter, digit, '-' or '.'
    for char in base_name:
        if not (char.islower() or char.isdigit() or char in '-.'):
            return False

    return True

def find_containerfile(directory, base_name):
    """Searches for a Containerfile based on the provided base name in the specified directory."""
    
    # Validate the base_name before proceeding
    if not is_valid_basename(base_name):
        raise ValueError(f"Invalid base name: '{base_name}'. Must only contain lowercase letters, digits, dashes, and periods.")

    containerfile_path = os.path.join(directory, f"{base_name}.Containerfile")
    if os.path.exists(containerfile_path):
        return containerfile_path
    else:
        raise FileNotFoundError(f"{base_name}.Containerfile not found in {directory}")

def get_image_name(base_name):
    """Generates a unique image name based on the base name."""
    image_name = f"{base_name}:latest"
    return image_name

def build_podman_image(containerfile_path, context_directory, image_name):
    """Builds a Podman image, showing output in real-time if any step after STEP 1 does not use cache."""
    
    build_command = [
        "podman", "build", 
        "-f", containerfile_path,  # Path to Containerfile
        "-t", image_name,       # Tag for the image
        context_directory       # Context directory
    ]

    # Start the build process with real-time output handling
    proc = subprocess.Popen(build_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8',)

    full_output = []  # To store full output in case we need to print it all later
    cache_used = True  # Track if all steps after STEP 1 use cache
    step = None        # Track the current step

    # Read the output in real-time
    for line in proc.stdout:
        full_output.append(line)  # Collect all output
        
        if step:
            # Check for cache usage in steps beyond STEP 1/n
            if "--> Using cache" not in line and not step.startswith("STEP 1/"):
                cache_used = False  # A step beyond STEP 1 is not using the cache, trigger full output
                break
            elif step.startswith("STEP 1/") and not line.startswith("STEP"):
                cache_used = False  # STEP 1 triggered a download
                break

        # If the line starts with "STEP ", it indicates the beginning of a new step
        if line.startswith("STEP"):
            step = line.strip()
        else:
            step = None

    # Print output in real-time if the cache is not used after STEP 1
    if not cache_used:
        print(f"Building image from {containerfile_path} as {image_name}:")
        print("".join(full_output), end="")
        for line in proc.stdout:
            print(line, end="")
    else:
        print(f"Nothing to do to build image {image_name}. Using cached version.")

    proc.wait()
        
    if not proc.returncode == 0:
        # If the build failed, print the full output regardless
        for line in full_output:
            print(line, end="")
        raise RuntimeError(f"Failed to build image {image_name}.")

def run_podman_container(image_name, mount_directory, additional_podman_args=[], additional_args=None, entrypoint=None):
    """Runs a Podman container using subprocess, mounting the directory and passing additional arguments."""

    run_command = [
        "podman", "run",
        "-it", # run interactively, as we assume to have a user present
        "--rm",  # Automatically remove the container after it exits
        "-v", f"{mount_directory}:/mnt",  # Mount the directory
    ]

    run_command += additional_podman_args

    if entrypoint:
        run_command += [
            "--entrypoint", entrypoint,
        ]

    run_command.append(image_name)  # Add the image name at the end

    if additional_args:
        run_command += additional_args
    
    # Execute the Podman run command
    print(f"{mount_directory} is mounted at /mnt")
    subprocess.run(run_command)

def prune_image(image_name):
    """Prunes (removes) the Podman image."""
    prune_command = ["podman", "rmi", image_name]
    print(f"Pruning image {image_name}...")
    result = subprocess.run(prune_command, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Image {image_name} removed successfully.")
    else:
        print(f"Error pruning image {image_name}: {result.stderr}")

def main():
    parser = argparse.ArgumentParser(description="Build and run Podman containers from a Containerfile.")

    subparsers = parser.add_subparsers(dest="command", help="Sub-command to run")

    # Subparser for the 'shell' command
    shell_parser = subparsers.add_parser("shell", help="Run an interactive shell in the container.")
    shell_parser.add_argument("base_name", help="Base name for the .Containerfile")

    # Subparser for the 'prune' command
    prune_parser = subparsers.add_parser("prune", help="Prune (remove) the image.")
    prune_parser.add_argument("base_name", help="Base name for the .Containerfile")

    # Subparser for the 'run' command
    run_parser = subparsers.add_parser("run", help="Run the container with specified arguments.")
    run_parser.add_argument("base_name", help="Base name for the .Containerfile")
    run_parser.add_argument("args", nargs=argparse.REMAINDER, help="Additional arguments to pass to the container.")

    # Global argument for directory
    parser.add_argument(
        "-d", "--directory", 
        help="Directory to search for the Containerfile and use as context. Defaults to current directory.", 
        default=os.getcwd()
    )

    parser.add_argument(
        "-v", "--volume", 
        help="Additional volume to mount (in 'source:destination' format).",
        action='append'
    )

    command_index = 1
    expect_arg_value = False
    for arg in sys.argv[1:]:
        if expect_arg_value or arg.startswith("-"):
            command_index += 1
            expect_arg_value = not expect_arg_value
        else:
            break

    # Assume 'run' commmand is desired if some unknown command name is entered
    if len(sys.argv) > command_index and sys.argv[command_index] not in ['shell', 'prune', 'run']:
        # Move the base_name argument to be after the command if an unknown command is given
        sys.argv.insert(command_index, "run")

    args = parser.parse_args()

    # Ensure the provided directory exists
    directory = os.path.abspath(args.directory)
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.")
        return
    
    try:
        # Step 1: Find the Containerfile
        containerfile_path = find_containerfile(directory, args.base_name)
        
        # Step 2: Generate the image name
        image_name = get_image_name(args.base_name)
        
        if args.command == "prune":
            # Prune (remove) the image
            prune_image(image_name)
        else:
            # Step 3: Build the image
            build_podman_image(containerfile_path, directory, image_name)
            
            podman_args = []
            if args.volume:
                for volume in args.volume:
                    podman_args += ['-v', volume]

            if args.command == "shell":
                default_shell = get_shell_env(image_name)
                
                # assume sh as a sane default if nothing else is specified
                if default_shell is None:
                    default_shell = "/bin/sh"
                
                run_podman_container(image_name, directory, additional_podman_args=podman_args, entrypoint=default_shell)
            elif args.command == "run":
                # Step 4: Run the container with passed arguments
                run_podman_container(image_name, directory, additional_podman_args=podman_args, additional_args=args.args)

    except Exception as e:
        print(f"Error: {e}")
        raise e

if __name__ == "__main__":
    main()
