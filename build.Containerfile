FROM python:3.12-slim

# Install pipx and poetry
RUN pip install --root-user-action ignore pipx
RUN pipx install poetry
ENV PATH="/root/.local/bin:${PATH}"
ENV SHELL="/bin/bash"

# Set the working directory in the container
WORKDIR /mnt

CMD ["/bin/bash", "-c", "poetry install && poetry build"]


