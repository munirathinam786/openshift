FROM squidfunk/mkdocs-material:9.5.24

# Set working directory
WORKDIR /docs

# Update pip version
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --upgrade pip

# Install missing packages
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org regex mkdocs-glightbox mkdocs-material-extensions

# mkdocs port
EXPOSE 8000
