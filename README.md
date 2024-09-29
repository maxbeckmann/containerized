
# Containerized / `crzd`- Podman Build and Run Tool

## Overview

**Containerized** is a Python tool designed for building and running rootless Podman containers seamlessly. It aims to streamline container workflows by automating the detection of `Containerfile`s, building images, and running containers, also interactively or with custom commands.

The tool establishes and relies on a few conventions around how a container must be organized, so certain things can be assumed safely. Details are available under Conventions below. This repo could be understood as a codification and documentaion of a few habits of mine in the creation and use of containers.   

The initial purpose of this project was to provide a language-agnostic way to create portable build environments but soon proved usefull for any occaisonal task requiring specific tooling. 

## Installation

To install **Containerized**, ensure you have `podman` and Python 3.12 or later installed. Use [Poetry](https://python-poetry.org/) to manage dependencies and install the project:

```sh
poetry install
```

After installation, you can use the CLI commands directly:

- `containerized`
- `crzd`

## Usage Semantics

The **Containerized** CLI provides a simple and flexible interface for interacting with Podman containers. Below is a detailed breakdown of how to use it:

```sh
containerized [-d DIRECTORY] [--shell [ENTRYPOINT]] [--prune] <base_name> [ARGS...]
```

### Arguments and Flags

- `<base_name>` (required): The base name for the `.Containerfile` to be used.
  - The tool will look for a file named `<base_name>.Containerfile` in the specified or current directory.
  
- `-d`, `--directory` (optional): 
  - Specifies the directory to search for the `Containerfile` and use as the build context.
  - Defaults to the current working directory if not specified.

- `--shell [ENTRYPOINT]` (optional):
  - Runs an interactive shell within the container.
  - The default entry point is `/bin/sh`. You can optionally specify a different entry point if needed.

- `--prune` (optional):
  - Removes the built image after the container stops running.
  - Useful for maintaining a clean environment and saving storage space.

- `ARGS...` (optional):
  - Any additional arguments to be passed to the container when it is run.
  - This allows for flexible command execution inside the container.

### Example Scenarios

1. **Build and Run a Container**:
   ```sh
   containerized my_containerfile
   ```
   This command searches for `my_containerfile.Containerfile` in the current directory, builds the image, and runs the container.

2. **Run an Interactive Shell in the Container**:
   ```sh
   containerized --shell my_containerfile
   ```
   This opens an interactive shell within the built container. It’s ideal for troubleshooting or exploring the container interactively.

3. **Run the Container with Custom Arguments**:
   ```sh
   containerized my_containerfile python script.py --arg value
   ```
   This command runs `script.py` within the container with the specified arguments. This is particularly useful for executing scripts or commands immediately after building the image.

4. **Prune the Image After Use**:
   ```sh
   containerized --prune my_containerfile
   ```
   This removes the built container image after running, helping to save disk space.

## Example Workflow with `crzd` Shortcut

The command `crzd` works identically to `containerized`, providing a more concise alias:

```sh
crzd .shell my_containerfile
```

This command runs the container using an interactive shell but uses a shorter command name for convenience.

## Error Handling and Edge Cases

- **Invalid Base Name**: The tool validates the `base_name` to ensure it only contains lowercase letters, digits, dashes, and periods. Invalid names will result in an error.
- **Containerfile Not Found**: If no matching `Containerfile` is found in the specified directory, an error is displayed.
- **Build Failures**: If the Podman build fails, the full build output is printed to help diagnose the issue.

## Conventions

To work seamlessly, `Containerfile`s should follow these design principles:
- The directory `containerized` is called on (explicitly through the `-d` flag or implicitly on your current working directory) will be mounted to the container at `/mnt/`. 
- The shell spawned for interactive usage will be learned from the `SHELL` environment variable. If it is omitted, `/bin/sh` is assumed. 

## License

This project is licensed under the MIT License. Please see the `LICENSE` file for details.

## Contributing

Contributions are welcome! If you'd like to add features or fix issues, please:

1. Fork the repository.
2. Create a new feature branch.
3. Submit a pull request with your changes.

## Future Improvement
- Explore use in Github Actions to facilitate portable building and deployment of projects
