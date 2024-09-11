#!/usr/bin/env python3

import os
import argparse
import subprocess

def find_containerfile(directory, base_name):
    """Searches for a Containerfile based on the provided base name in the specified directory."""
    containerfile_path = os.path.join(directory, f"{base_name}.Containerfile")
    if os.path.exists(containerfile_path):
        return containerfile_path
    else:
        raise FileNotFoundError(f"{base_name}.Containerfile not found in {directory}")

def get_image_name(base_name):
    """Generates a unique image name based on the base name."""
    image_name = f"build_{base_name}:latest"
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

def run_podman_container(image_name, mount_directory, additional_args=None, entrypoint=None):
    """Runs a Podman container using subprocess, mounting the directory and passing additional arguments."""
    
    current_uid = os.getuid()
    current_gid = os.getgid()

    run_command = [
        "podman", "run",
        "--rm",  # Automatically remove the container after it exits
        "-v", f"{mount_directory}:/mnt",  # Mount the directory
    ]

    if entrypoint:
        run_command += [
            "--entrypoint", entrypoint, 
            "-it"
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
    
    # Positional argument for the base name of the Containerfile
    parser.add_argument("base_name", help="Base name for the .Containerfile")
    
    # Global argument for directory
    parser.add_argument(
        "-d", "--directory", 
        help="Directory to search for the Containerfile and use as context. Defaults to current directory.", 
        default=os.getcwd()
    )

    # Flag for shell mode, with optional binary path for the entry point
    parser.add_argument(
        "--shell", nargs="?", const="/bin/sh", 
        help="Run an interactive shell in the container. Optionally specify a binary as the entry point."
    )

    # Subcommand: prune (to remove the image)
    parser.add_argument(
        "--prune", action="store_true", 
        help="Prune (remove) the image created by the tool."
    )

    # Additional arguments to pass to the container
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Additional arguments to pass to the container.")

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
        
        if args.prune:
            # Prune (remove) the image
            prune_image(image_name)
        else:
            # Step 3: Build the image
            build_podman_image(containerfile_path, directory, image_name)
            
            # Step 4: Run the container with the optional shell flag or passed arguments
            if args.shell:
                run_podman_container(image_name, directory, entrypoint=args.shell)
            else:
                run_podman_container(image_name, directory, additional_args=args.args)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
