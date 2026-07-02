import re
with open('requirements.txt', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('#'):
        new_lines.append(line)
        continue
    # Strip version constraints but keep markers
    # Example: 'gevent==21.8.0 ; sys_platform != "win32"' -> 'gevent ; sys_platform != "win32"'
    new_line = re.sub(r'==[0-9\.]+', '', line)
    new_lines.append(new_line)

with open('requirements_unpinned.txt', 'w') as f:
    f.writelines(new_lines)
