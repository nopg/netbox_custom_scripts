**Standard Circuit**
```mermaid
graph LR
A[Device/Interface] --> B["Patch Panel (optional)"]
B --> C[Site/Circuit]
C --> D[Provider Network]
```

**Point-to-Point Circuit**
```mermaid
graph LR
A[Device/Interface] --> B["Patch Panel (optional)"]
B --> C[Site A]
C --> D[Circuit]
D --> E[Site Z]
E --> F["Patch Panel (optional)"]
F --> G[Device/Interface]
```

**Meet Me Circuit**
```mermaid
graph LR
A[Device/Interface] --> B["Patch Panel A"]
B --> C["Patch Panel Z"]
C --> D[Site/Circuit]
D --> E[Provider Network]