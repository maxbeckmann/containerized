#!/usr/bin/env python3

import os
import argparse
import subprocess

def find_containerfile(directory):
    """Searches for a build.Containerfile in the specified directory."""
    containerfile_path = os.path.join(directory, "build.Containerfile")
    if os.path.exists(containerfile_path):
        return containerfile_path
    else:
        raise FileNotFoundError(f"build.Containerfile not found in {directory}")

def get_image_name(directory):
    """Generates a unique image name based on the directory name."""
    dir_name = os.path.basename(directory)
    image_name = f"build_{dir_name}:latest"
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
    proc = subprocess.Popen(build_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

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
                cache_used = False # STEP 1 triggered a download
                break

        # If the line starts with "STEP ", it indicates the beginning of a new step
        if line.startswith("STEP"):
            step = line.strip()
        else:
            step = None

    # Print output in real-time if the cache is not used after STEP 1
    # If the image was fully built from cache beyond STEP 1, suppress the output and show a summary
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

def run_podman_container(image_name, mount_directory, interactive=False):
    """Runs a Podman container using subprocess, mounting the directory."""

    current_uid = os.getuid()
    current_gid = os.getgid()

    run_command = [
        "podman", "run",
        "--rm",  # Automatically remove the container after it exits
        "-v", f"{mount_directory}:/mnt",  # Mount the directory
    ]

    if interactive:
        run_command += ["-it", "--entrypoint", "/bin/sh"]  # Interactive terminal with shell
    
    run_command.append(image_name)  # Run the default command of the image
    
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
    parser = argparse.ArgumentParser(description="Build and run Podman containers from Containerfile.")
    
    # Global arguments
    parser.add_argument(
        "-d", "--directory", 
        help="Directory to search for build.Containerfile and use as context. Defaults to current directory.", 
        default=os.getcwd()
    )

    # Subcommands: build, shell, and prune
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build and run the default command in the container.")
    
    shell_parser = subparsers.add_parser("shell", help="Build and run an interactive shell in the container.")
    
    prune_parser = subparsers.add_parser("prune", help="Prune (remove) the image created by the tool.")

    args = parser.parse_args()

    # Ensure the provided directory exists
    directory = os.path.abspath(args.directory)
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.")
        return
    
    try:
        # Step 1: Find the Containerfile
        containerfile_path = find_containerfile(directory)
        
        # Step 2: Generate the image name
        image_name = get_image_name(directory)
        
        # Step 3: Execute the command based on the user's choice
        if args.command == "build":
            # Build the image and run container with the default command
            build_podman_image(containerfile_path, directory, image_name)
            run_podman_container(image_name, directory)
        elif args.command == "shell":
            # Build the image and run container with an interactive shell
            build_podman_image(containerfile_path, directory, image_name)
            run_podman_container(image_name, directory, interactive=True)
        elif args.command == "prune":
            # Prune (remove) the image
            prune_image(image_name)
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
