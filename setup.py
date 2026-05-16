from setuptools import setup, find_packages
# pip install -e . 会启动该文件，
# 然后把cli命令打包到venv中
# 然后就可以使用 cybercode 命令了
# 例如：cybercode config
# 例如：cybercode run

# 读取 requirements.txt
def parse_requirements(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#')
        ]


setup(
    name="cyber-code",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["cli"], 
    install_requires=parse_requirements('requirements.txt'),
    entry_points={
        "console_scripts": [
            "cybercode=entry.cli:main",
        ],
    },
)
