const roles = {
    customer: {
        label: "Customer guide",
        title: "Buy tickets and use them at the event",
        copy: "This page only shows the customer workflow: choosing tickets, checking out, finding the confirmation, and using the QR code."
    },
    organizer: {
        label: "Organizer guide",
        title: "Create events and run ticket sales",
        copy: "This page only shows organizer work: creating events, tickets, quotas, public pages, teams, and launch checks."
    },
    staff: {
        label: "Event staff guide",
        title: "Manage orders and support one event",
        copy: "This page only shows event staff work: finding orders, helping customers, checking sales, and escalating sensitive changes."
    },
    checkin: {
        label: "Check-in guide",
        title: "Scan tickets and manage entry",
        copy: "This page only shows entrance work: check-in lists, devices, scan results, and what to do when a ticket has a problem."
    },
    admin: {
        label: "Administrator guide",
        title: "Install, secure, and maintain tiks",
        copy: "This page only shows administrator work: installation, server settings, organizer creation, backups, and operations."
    },
    all: {
        label: "Complete guide",
        title: "Learn tiks one role at a time",
        copy: "This complete view is for training and internal review. In the main tiks system, each role opens its own guide."
    }
};

function selectedRole() {
    const params = new URLSearchParams(window.location.search);
    const role = (params.get("role") || "customer").toLowerCase();
    return roles[role] ? role : "customer";
}

function sectionAllowsRole(section, role) {
    const value = section.dataset.role;
    if (!value || role === "all") {
        return true;
    }
    if (value === "all") {
        return false;
    }
    return value.split(/\s+/).includes(role);
}

function applyRole() {
    const role = selectedRole();
    const config = roles[role];

    document.body.dataset.currentRole = role;
    document.title = `tiks Documentation - ${config.label}`;
    document.getElementById("role-kicker").textContent = config.label;
    document.getElementById("hero-title").textContent = config.title;
    document.getElementById("hero-copy").textContent = config.copy;

    document.querySelectorAll("[data-role-link]").forEach((link) => {
        link.classList.toggle("active", link.dataset.roleLink === role);
        link.classList.toggle("hidden-role", role !== "all" && link.dataset.roleLink !== role);
    });

    document.querySelectorAll("[data-role]").forEach((section) => {
        section.classList.toggle("hidden-role", !sectionAllowsRole(section, role));
    });
}

function improveExternalLinks() {
    document.querySelectorAll("a[href^='http']").forEach((link) => {
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener");
    });
}

document.addEventListener("DOMContentLoaded", () => {
    applyRole();
    improveExternalLinks();
});
