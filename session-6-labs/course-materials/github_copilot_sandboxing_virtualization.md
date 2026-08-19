## Sandboxing and Virtualization: From Containers to MicroVMs

When running untrusted or semi-trusted workloads—such as applications, plugins, CI jobs, or AI agents—we want **isolation**. The key question is:

> **How much of the host operating system does the workload share, and how strong is the isolation boundary?**

A useful way to understand modern sandboxing technologies is to move from **shared-kernel containers** toward **virtual machines**:

**Shared-kernel container → gVisor → Firecracker microVM → Kata microVM**

The isolation generally becomes stronger as we introduce a separate kernel and hardware-virtualization boundary, although there are important differences in architecture and performance.

---

# 1. Shared-Kernel Containers

A traditional Linux container, such as one created with Docker or containerd, **does not contain its own operating-system kernel**.

Instead, multiple containers use the **same Linux kernel as the host**.

For example:

```text
+-------------------------------------------------------+
|                    Host Linux Kernel                  |
|                                                       |
|   +-------------+   +-------------+   +-------------+ |
|   | Container A |   | Container B |   | Container C | |
|   |             |   |             |   |             | |
|   | App         |   | App         |   | App         | |
|   | Libraries   |   | Libraries   |   | Libraries   | |
|   +-------------+   +-------------+   +-------------+ |
|                                                       |
+-------------------------------------------------------+
|                     Hardware                          |
+-------------------------------------------------------+
```

Containers use Linux kernel mechanisms such as:

* **Namespaces** — isolate processes, networking, mounts, users, etc.
* **cgroups** — control CPU, memory, and other resources.
* **Capabilities** — restrict privileged operations.
* **seccomp** — restrict system calls.
* **Linux Security Modules**, such as AppArmor or SELinux.

### Why is this important for security?

Suppose an application inside a container executes:

```text
Application
    ↓
System call
    ↓
Host Linux kernel
```

The application ultimately interacts with the **same kernel that controls the host**.

Therefore, a vulnerability in the kernel or a sufficiently powerful container escape can potentially compromise the host.

This doesn't mean containers are inherently insecure. Properly configured containers provide substantial isolation and are extremely useful. However, their fundamental security boundary is different from that of a virtual machine.

### Main advantage

Containers are:

* lightweight
* fast to start
* resource efficient
* highly compatible with existing cloud-native infrastructure

### Main limitation

**The kernel is shared.**

---

# 2. gVisor

gVisor takes a different approach.

gVisor is a **sandboxing technology that implements a large portion of the Linux system-call interface in userspace**.

Instead of allowing the application to communicate directly with the host kernel for many operations, gVisor introduces an additional isolation layer.

Conceptually:

```text
+------------------------------------------------------+
|                   Host Linux Kernel                  |
|                                                      |
|   +----------------------------------------------+   |
|   |                    gVisor                    |   |
|   |                                              |   |
|   |   Application → gVisor system-call layer    |   |
|   |                                              |   |
|   +----------------------------------------------+   |
|                                                      |
+------------------------------------------------------+
|                     Hardware                         |
+------------------------------------------------------+
```

A simplified execution path becomes:

```text
Application
     |
     | system call
     v
gVisor sandbox
     |
     | controlled interaction
     v
Host kernel
```

This means that the application has **less direct exposure to the host kernel**.

### Why is gVisor useful?

Imagine that an application is compromised:

```text
Untrusted application
        |
        v
   Exploit attempt
        |
        v
    gVisor layer
        |
        X
   Reduced access
   to host kernel
```

An attacker must overcome an additional security boundary.

### Important characteristic

gVisor is **not simply a traditional virtual machine**.

It provides a sandboxed environment using a userspace kernel-like layer rather than giving every workload a complete conventional guest operating system.

### Trade-off

The additional isolation can introduce:

* compatibility limitations
* additional overhead
* performance differences for workloads with intensive system-call activity

However, it can provide stronger isolation than relying exclusively on traditional containers.

---

# 3. Firecracker MicroVM

Firecracker takes another step toward traditional virtualization.

Firecracker is a **virtual machine monitor (VMM)** designed specifically for lightweight workloads.

It uses hardware virtualization, typically through **KVM on Linux**, to run a guest kernel in a virtual machine.

Conceptually:

```text
+-------------------------------------------------------+
|                     Host Linux                        |
|                                                       |
|   +---------------- Firecracker ------------------+   |
|   |                                               |   |
|   |       +-------------------------------+       |   |
|   |       |        Guest Linux Kernel     |       |   |
|   |       |                               |       |   |
|   |       |       Application              |       |   |
|   |       +-------------------------------+       |   |
|   +-----------------------------------------------+   |
|                                                       |
+-------------------------------------------------------+
|                     Hardware                          |
+-------------------------------------------------------+
```

The important difference is:

> **The workload gets its own guest kernel.**

Instead of:

```text
Application → Host kernel
```

we have:

```text
Application
     ↓
Guest kernel
     ↓
Virtual hardware
     ↓
Firecracker
     ↓
Host kernel
     ↓
Hardware
```

The virtualization boundary therefore provides stronger isolation than a traditional shared-kernel container.

### Why "micro" VM?

A conventional VM may emulate or expose many virtual hardware components.

Firecracker deliberately provides a **minimal virtual machine device model** designed for fast startup and a small attack surface.

This makes it particularly appropriate for:

* serverless workloads
* multi-tenant computing
* isolated execution
* sandboxed applications
* short-lived workloads

Firecracker was developed by AWS and is used as the virtualization foundation for services such as AWS Lambda and AWS Fargate.

### Security perspective

If an application compromises its guest kernel, the attacker still needs to cross the **virtual-machine boundary** to reach the host.

That is a fundamentally different security model from a traditional container.

---

# 4. Kata Containers and Kata MicroVMs

Kata Containers combines the **container experience** with **virtual-machine isolation**.

Kata Containers is designed so that a container can appear to the container orchestration system much like a normal container while actually running inside a lightweight virtual machine.

Conceptually:

```text
+---------------------------------------------------------+
|                    Host Linux Kernel                    |
|                                                         |
|   +---------------- Kata Runtime -------------------+   |
|   |                                                  |   |
|   |       +----------------------------------+       |   |
|   |       |        Kata Guest VM             |       |   |
|   |       |                                  |       |   |
|   |       |  Guest Kernel                    |       |   |
|   |       |       ↓                          |       |   |
|   |       |  Container / Application         |       |   |
|   |       +----------------------------------+       |   |
|   +--------------------------------------------------+   |
|                                                         |
+---------------------------------------------------------+
|                       Hardware                          |
+---------------------------------------------------------+
```

The key idea is:

> **Containers are managed like containers, but workloads receive VM-level isolation.**

This is particularly useful in environments where different customers, applications, or teams share the same infrastructure.

Kata can use different virtualization technologies and VMMs depending on its configuration and platform. Therefore, **Kata Containers and Firecracker are not exactly equivalent technologies**:

* Firecracker is primarily a **VMM/microVM technology**.
* Kata Containers is a **container runtime architecture that uses lightweight VMs for isolation**.

---

# 5. Comparing the Four Approaches

| Characteristic             | Shared-kernel container   | gVisor                                               | Firecracker microVM            | Kata Containers / microVM              |
| -------------------------- | ------------------------- | ---------------------------------------------------- | ------------------------------ | -------------------------------------- |
| Basic technology           | OS-level virtualization   | Sandbox / userspace kernel                           | MicroVM / VMM                  | Container runtime + VM isolation       |
| Kernel                     | **Shared host kernel**    | Host kernel plus gVisor isolation layer              | **Separate guest kernel**      | **Separate guest kernel**              |
| Hardware virtualization    | No                        | Generally no                                         | **Yes**                        | **Yes**                                |
| Isolation boundary         | Linux kernel mechanisms   | Additional sandbox boundary                          | Virtual-machine boundary       | Virtual-machine boundary               |
| Typical isolation strength | Good                      | Stronger than standard containers for many workloads | Very strong                    | Very strong                            |
| Startup time               | Very fast                 | Very fast                                            | Very fast for a VM             | Fast                                   |
| Resource overhead          | Very low                  | Low to moderate                                      | Low                            | Low to moderate                        |
| Compatibility              | Very high                 | Some system-call limitations                         | Requires guest OS/kernel       | Generally container-compatible         |
| Attack surface             | Host kernel               | Host kernel + sandbox components                     | VMM + guest kernel + host      | Runtime + VMM + guest kernel + host    |
| Typical use                | Cloud-native applications | Untrusted containers                                 | Serverless / strong isolation  | Kubernetes multi-tenancy               |
| Kubernetes integration     | Native                    | Runtime integration                                  | Requires integration           | **Designed for containers/Kubernetes** |
| Main security idea         | Isolate processes         | Reduce direct kernel exposure                        | Isolate through virtualization | Combine containers with VM isolation   |

---

# 6. The Most Important Concept: The Kernel Boundary

For an introductory class, the easiest way to remember the difference is to focus on **where the kernel boundary is**.

### Shared-kernel container

```text
Application
     ↓
 SAME HOST KERNEL
     ↓
Hardware
```

**One kernel for everyone.**

---

### gVisor

```text
Application
     ↓
gVisor sandbox
     ↓
Host kernel
     ↓
Hardware
```

**An additional software isolation layer protects the host kernel from direct application interaction.**

---

### Firecracker

```text
Application
     ↓
Guest kernel
     ↓
Virtual hardware
     ↓
Firecracker
     ↓
Host kernel
     ↓
Hardware
```

**The application has its own guest kernel.**

---

### Kata

```text
Container
     ↓
Guest kernel
     ↓
MicroVM
     ↓
Host kernel
     ↓
Hardware
```

**A container interface is combined with VM-level isolation.**

---

# 7. An Analogy for Students

Imagine a university with several students.

### Shared-kernel containers: different rooms in the same building

Students have separate rooms, but they share the same building infrastructure.

```text
+--------------------------------+
|          Building             |
|  +------+ +------+ +------+   |
|  | A    | | B    | | C    |   |
|  +------+ +------+ +------+   |
+--------------------------------+
```

If the building's fundamental infrastructure has a serious vulnerability, all rooms can potentially be affected.

---

### gVisor: rooms with an additional security checkpoint

Students still use the same building, but there is an additional controlled interface between their rooms and the building infrastructure.

---

### MicroVM: separate small buildings

Each student receives a small independent building:

```text
+---------+    +---------+    +---------+
| VM A    |    | VM B    |    | VM C    |
| Kernel  |    | Kernel  |    | Kernel  |
+---------+    +---------+    +---------+
       \            |             /
        +-----------+------------+
                    |
                Host system
```

There is considerably more separation between students.

---

### Kata: small buildings managed as if they were rooms

From the university administrator's perspective, the students can still be managed using a familiar "room management" system, but each room is actually backed by a small independent building.

This is analogous to the goal of Kata:

> **Container-oriented management + VM-oriented isolation.**

---

# 8. Security vs. Performance

A useful engineering principle is that **isolation is not free**.

A simplified spectrum is:

```text
                 Increasing isolation
                        ───────────────>

Shared             gVisor          MicroVM
containers           │               │
   │                 │               │
   ▼                 ▼               ▼
+------+          +------+        +------+
| App  |          | App  |        | App  |
+------+          +------+        +------+
   │                 │               │
   ▼                 ▼               ▼
Host kernel       gVisor          Guest kernel
                                     │
                                     ▼
                                  VMM
                                     │
                                     ▼
                                Host kernel
```

Generally:

**More isolation → more components → potentially more overhead.**

But modern microVM technologies are specifically designed to minimize that overhead.

Therefore, the engineering decision should not simply be:

> "Which technology is most secure?"

Instead, ask:

> **"What level of isolation does my threat model require, and what performance and compatibility constraints do I have?"**

---

# 9. When Would You Use Each?

### Shared-kernel containers

Good choice when:

* workloads are trusted or moderately trusted
* performance is important
* high container density is required
* Kubernetes/container orchestration is the primary environment

**Example:**
A company's internal microservices running in Kubernetes.

---

### gVisor

Good choice when:

* workloads are less trusted
* you want stronger isolation than traditional containers
* you want to retain a container-oriented workflow
* complete VM isolation is not necessary

**Example:**
Running potentially untrusted user workloads in a cloud platform.

---

### Firecracker

Good choice when:

* strong isolation is required
* workloads are highly dynamic or untrusted
* fast VM startup is important
* minimizing the VMM attack surface is important

**Example:**
A serverless platform executing code belonging to different customers.

---

### Kata Containers

Good choice when:

* you want container/Kubernetes semantics
* workloads require stronger isolation
* multiple tenants share infrastructure
* VM-level isolation is desirable without abandoning the container ecosystem

**Example:**
A Kubernetes cluster hosting workloads from different customers.

---

# 10. A Useful Mental Model

For an introductory engineering course, I would summarize the technologies with four questions:

| Question                            | Shared Container | gVisor                              | Firecracker    | Kata    |
| ----------------------------------- | ---------------- | ----------------------------------- | -------------- | ------- |
| Do I share the host kernel?         | **Yes**          | Partially/direct access is mediated | **No**         | **No**  |
| Do I have a separate guest kernel?  | No               | No                                  | **Yes**        | **Yes** |
| Do I use hardware virtualization?   | No               | No                                  | **Yes**        | **Yes** |
| Am I primarily managing containers? | **Yes**          | **Yes**                             | Not inherently | **Yes** |

### The key takeaway

> **Containers isolate processes; gVisor adds a sandbox boundary; microVMs isolate workloads through virtualization; Kata combines the container model with VM-level isolation.**

This distinction is especially important for **sandboxing untrusted code**, including CI/CD jobs, multi-tenant applications, plugin systems, serverless functions, and increasingly **AI/LLM agents that can execute tools or generate and run code**.
