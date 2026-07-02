/** @odoo-module */
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class BalanceSheetReport extends Component {
    static template = "gdr_balance_sheet.BalanceSheetReport";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        const today = luxon.DateTime.now();
        this.state = useState({
            lines: [],
            dateFrom: "",
            dateTo: today.toFormat("yyyy-MM-dd"),
            dateToDisplay: today.toFormat("MM/dd/yyyy"),
            targetMove: "posted",
            expandedState: {},
            loading: true,
            hasUnposted: false,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "gdr.balance.sheet",
                "get_report_data",
                [],
                {
                    date_from: this.state.dateFrom || null,
                    date_to: this.state.dateTo,
                    target_move: this.state.targetMove,
                }
            );
            this.state.lines = data.lines;
            this.state.dateToDisplay = data.date_to;
            this.state.hasUnposted = data.has_unposted;
        } catch (e) {
            console.error("Error loading balance sheet data:", e);
        }
        this.state.loading = false;
    }

    async onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        await this.loadData();
    }

    async onDateChange(ev) {
        this.state.dateTo = ev.target.value;
        await this.loadData();
    }

    async onTargetMoveChange(ev) {
        this.state.targetMove = ev.target.value;
        await this.loadData();
    }

    /**
     * Event delegation handler: reads data-line-id from the clicked row
     */
    onRowClick(ev) {
        const row = ev.target.closest("tr[data-line-id]");
        if (!row) return;
        const lineId = row.dataset.lineId;
        this.toggleLine(lineId);
    }

    toggleLine(lineId) {
        if (!this.hasChildren(lineId)) return;
        const currentlyExpanded = this.isExpanded(lineId);
        this.state.expandedState = {
            ...this.state.expandedState,
            [lineId]: !currentlyExpanded
        };
    }

    isExpanded(lineId) {
        const line = this.state.lines.find((l) => String(l.id) === String(lineId));
        if (!line) return false;
        if (lineId in this.state.expandedState) {
            return this.state.expandedState[lineId];
        }
        // Sections and groups default to expanded
        if (line.is_section || line.is_group) return true;
        return false;
    }

    isLineVisible(line) {
        if (!line.parent_id) return true;
        let parentId = line.parent_id;
        while (parentId) {
            if (!this.isExpanded(parentId)) return false;
            const parent = this.state.lines.find((l) => String(l.id) === String(parentId));
            if (!parent) break;
            parentId = parent.parent_id;
        }
        return true;
    }

    hasChildren(lineId) {
        return this.state.lines.some((l) => String(l.parent_id) === String(lineId));
    }

    formatAmount(amount) {
        if (amount === undefined || amount === null || amount === 0) return "";
        const negative = amount < 0;
        const abs = Math.abs(amount);
        const formatted = abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return negative ? `-${formatted}` : formatted;
    }

    getLineClass(line) {
        const classes = [`bs-level-${line.level}`];
        if (line.is_section) classes.push("bs-section");
        if (line.is_group) classes.push("bs-group");
        if (line.is_leaf) classes.push("bs-leaf");
        if (line.is_account) classes.push("bs-account");
        if (line.is_total) classes.push("bs-total");
        if (line.balance < 0) classes.push("bs-negative");
        return classes.join(" ");
    }

    getAmountClass(line) {
        if (line.balance < 0) return "bs-amount bs-negative-amount";
        return "bs-amount";
    }

    async onPdfClick() {
        window.print();
    }

    async onXlsxClick() {
        let csv = "Name,Balance\n";
        for (const line of this.state.lines) {
            if (this.isLineVisible(line)) {
                const indent = "  ".repeat(line.level);
                csv += `"${indent}${line.name}",${line.balance || 0}\n`;
            }
        }
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Balance_Sheet_${this.state.dateTo}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    unfoldAll() {
        const newState = { ...this.state.expandedState };
        for (const line of this.state.lines) {
            if (this.hasChildren(line.id)) {
                newState[String(line.id)] = true;
            }
        }
        this.state.expandedState = newState;
    }

    foldAll() {
        const newState = { ...this.state.expandedState };
        for (const line of this.state.lines) {
            if (line.is_section) {
                newState[String(line.id)] = true;
            } else if (line.is_group || line.is_leaf) {
                newState[String(line.id)] = false;
            }
        }
        this.state.expandedState = newState;
    }
}

registry.category("actions").add("gdr_balance_sheet_report", BalanceSheetReport);
