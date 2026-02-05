"""
로그 수집 클라이언트 라이브러리 설치 스크립트
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="log-collector-async",
    version="1.1.1",
    author="Log Analysis System Team",
    author_email="jack1087902@gmail.com",
    description="비동기 로그 수집 클라이언트",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/log-analysis-system",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/log-analysis-system/issues",
        "Documentation": "https://github.com/yourusername/log-analysis-system/blob/main/clients/python/README.md",
        "Source Code": "https://github.com/yourusername/log-analysis-system/tree/main/clients/python",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Logging",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ]
    }
)
