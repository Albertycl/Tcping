<template>
  <div>
    <v-btn
      class="mb-1 blue-grey lighten-4"
      depressed
      @click="copyToClipboard(tcping_or_mtr_result)"
    >
      copy to clipboard</v-btn
    >
    <p class="blue-grey lighten-4 pa-2 rounded">
      <span class="blue--text text--darken-3 font-weight-medium"
        >{{ isp_name }}_{{ linux_hostname }}_{{ probe_ip }}</span
      >
      /
      <span
        class="cyan lighten-4 pa-1 rounded text-h6 blue--text text--darken-2"
        >public ip:{{ linux_public_ip }}</span
      >
      <v-btn
        v-if="!linux_public_ip && probe_id"
        x-small
        color="warning"
        :loading="isUpdatingIp"
        @click="updatePublicIp"
        class="ml-2"
      >
        Update IP
      </v-btn>
    </p>
    <div id="pre_text_tcp_trace_route">
      <!-- Route Loop Warning -->
      <v-alert
        v-if="routeLoopInfo.hasLoop"
        type="warning"
        dense
        outlined
        class="mb-2"
      >
        <v-icon small color="warning" class="mr-1">mdi-alert-circle</v-icon>
        <strong>Route Loop Detected!</strong>
        IP
        <span class="font-weight-bold">{{
          routeLoopInfo.loopIps.join(", ")
        }}</span>
        appears multiple times in the trace route.
      </v-alert>
      <!-- Error Message Display -->
      <div v-if="parsedMtrData.hasError" class="error-container pa-4">
        <v-alert type="error" dense outlined>
          <div class="font-weight-bold mb-2">Probe Error</div>
          <div>{{ parsedMtrData.errorMessage }}</div>
        </v-alert>
      </div>
      <!-- Parsed Table View -->
      <div
        v-else-if="parsedMtrData.hops.length > 0"
        class="mtr-table-container"
      >
        <div class="mtr-header mb-1">
          <span class="text-caption">{{ parsedMtrData.startTime }}</span>
          <span class="ml-2 font-weight-bold">{{ parsedMtrData.host }}</span>
        </div>
        <v-simple-table dense class="mtr-table">
          <thead>
            <tr class="blue-grey lighten-3">
              <th class="text-center" style="width: 30px">#</th>
              <th class="text-left" style="width: 70px">ASN</th>
              <th class="text-left" style="width: 120px">IP</th>
              <th class="text-left">ISP</th>
              <th class="text-center" style="width: 60px">Loss%</th>
              <th class="text-center" style="width: 40px">Snt</th>
              <th class="text-center" style="width: 55px">Last</th>
              <th class="text-center" style="width: 55px">Avg</th>
              <th class="text-center" style="width: 55px">Best</th>
              <th class="text-center" style="width: 55px">Wrst</th>
              <th class="text-center" style="width: 55px">StDev</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(hop, index) in parsedMtrData.hops"
              :key="index"
              :class="getHopRowClass(hop)"
            >
              <td class="text-center">{{ hop.num }}</td>
              <td
                class="text-left font-weight-medium"
                :class="
                  hop.asNumber ? 'teal--text text--darken-2' : 'grey--text'
                "
              >
                {{ hop.asNumber || hop.asn || "-" }}
              </td>
              <td class="text-left font-weight-medium">
                {{ hop.ip }}
              </td>
              <td class="text-left text-caption grey--text text--darken-1">
                {{ hop.ispName || "-" }}
              </td>
              <td
                class="text-center font-weight-bold"
                :class="getLossClass(hop.loss)"
              >
                {{ hop.loss }}
              </td>
              <td class="text-center">{{ hop.snt }}</td>
              <td class="text-center">{{ hop.last }}</td>
              <td class="text-center font-weight-medium">{{ hop.avg }}</td>
              <td class="text-center green--text text--darken-2">
                {{ hop.best }}
              </td>
              <td class="text-center" :class="getWorstClass(hop.wrst, hop.avg)">
                {{ hop.wrst }}
              </td>
              <td class="text-center">{{ hop.stdev }}</td>
            </tr>
          </tbody>
        </v-simple-table>
      </div>
      <!-- Loading state when batch started but no data yet -->
      <div
        v-else-if="!tcping_or_mtr_result && isBatchInProgress"
        class="loading-container pa-4 text-center"
      >
        <v-progress-circular
          indeterminate
          color="primary"
          size="24"
          class="mr-2"
        ></v-progress-circular>
        <span class="grey--text">Waiting for probe data...</span>
      </div>
      <!-- Placeholder before batch starts -->
      <div v-else-if="!tcping_or_mtr_result" class="pa-4 text-center">
        <span class="grey--text text--lighten-1">Click START to begin</span>
      </div>
      <!-- Fallback to raw text if parsing fails -->
      <pre v-else :class="resultClass">{{ tcping_or_mtr_result }}</pre>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  props: [
    "probe_ip",
    "probe_id",
    "linux_hostname",
    "linux_public_ip",
    "isp",
    "isp_name",
    "storeKey"
  ],
  data() {
    return {
      is_dns_error: false,
      isUpdatingIp: false
    };
  },

  updated() {
    this.scrollToEnd();
  },
  methods: {
    scrollToEnd() {
      var container = this.$el.querySelector("#pre_text_tcp_trace_route");
      console.log(`container=${container}`);
      container.scrollTop = container.scrollHeight;
    },
    copyToClipboard(text) {
      // Remove completion markers before copying
      var cleanText = text
        .replace("---TCPING_COMPLETE---", "")
        .replace("---MTR_COMPLETE---", "")
        .replace("---DIG_COMPLETE---", "")
        .trim();
      var dummy = document.createElement("textarea");
      document.body.appendChild(dummy);
      dummy.value = cleanText;
      dummy.select();
      try {
        var successful = document.execCommand("copy");
        var msg = successful ? "successful" : "unsuccessful";
        alert("Result copied " + msg);
      } catch (err) {
        alert("Oops, unable to copy");
      }
      document.body.removeChild(dummy);
    }, //end of copyToClipboard
    getLossClass(loss) {
      if (!loss) return "";
      const lossNum = parseFloat(loss);
      if (lossNum === 0) return "green--text text--darken-2";
      if (lossNum < 10) return "orange--text text--darken-2";
      return "red--text text--darken-2";
    },
    getWorstClass(wrst, avg) {
      if (!wrst || !avg) return "";
      const wrstNum = parseFloat(wrst);
      const avgNum = parseFloat(avg);
      if (wrstNum > avgNum * 3) return "red--text";
      if (wrstNum > avgNum * 2) return "orange--text";
      return "";
    },
    getHopRowClass(hop) {
      // Check if this hop is part of a route loop
      if (this.isHopInLoop(hop)) {
        return "deep-orange lighten-4";
      }
      if (!hop.loss) return "";
      const lossNum = parseFloat(hop.loss);
      if (lossNum >= 50) return "red lighten-5";
      if (lossNum > 0) return "amber lighten-5";
      return "";
    },
    isHopInLoop(hop) {
      if (!hop.ip || hop.ip === "???" || !this.routeLoopInfo.hasLoop)
        return false;
      // Check if this hop's IP is one of the looping IPs
      const ips = hop.ip.split(",").map(s => s.trim());
      for (const ip of ips) {
        if (
          this.routeLoopInfo.loopIps.some(loopIp => loopIp.startsWith(ip + " "))
        ) {
          return true;
        }
      }
      return false;
    },
    async updatePublicIp() {
      this.isUpdatingIp = true;
      try {
        const response = await axios.post(
          `/api/update_probe_public_ip/${this.probe_id}`
        );
        if (response.data.success) {
          this.$emit("public-ip-updated", {
            probeId: this.probe_id,
            newPublicIp: response.data.public_ip
          });
          alert(`Public IP updated to: ${response.data.public_ip}`);
        } else {
          alert(`Failed to update: ${response.data.error}`);
        }
      } catch (error) {
        console.error("Error updating public IP:", error);
        const errorMsg =
          error.response?.data?.error || error.message || "Unknown error";
        alert(`Error: ${errorMsg}`);
      } finally {
        this.isUpdatingIp = false;
      }
    }
  },

  computed: {
    // Get result from Vuex (populated by parent's batch SSE)
    // storeKey prop allows using separate state for ALL-IN-ONE page
    tcping_or_mtr_result() {
      if (this.storeKey === "mtr") {
        return this.$store.state.mtrProbeResults[this.probe_ip] || "";
      }
      return this.$store.state.probeResults[this.probe_ip] || "";
    },
    isComplete() {
      if (this.storeKey === "mtr") {
        return this.$store.state.mtrProbeCompleted[this.probe_ip] || false;
      }
      return this.$store.state.probeCompleted[this.probe_ip] || false;
    },
    isBatchInProgress() {
      if (this.storeKey === "mtr") {
        return this.$store.state.mtrBatchInProgress || false;
      }
      return this.$store.state.batchInProgress || false;
    },
    parsedMtrData() {
      const result = {
        startTime: "",
        host: "",
        hops: [],
        hasError: false,
        errorMessage: ""
      };
      if (!this.tcping_or_mtr_result) return result;

      // Check for error conditions - don't try to parse if there's an error
      const errorPatterns = [
        "upstream request timeout",
        "API rejected",
        "measurement timed out",
        "probe may be offline",
        "error:",
        "Cannot resolve host",
        "Failed to resolve host",
        "SSH connection aborted",
        "cannot tcping to port"
      ];

      for (const pattern of errorPatterns) {
        if (this.tcping_or_mtr_result.includes(pattern)) {
          result.hasError = true;
          result.errorMessage = this.tcping_or_mtr_result;
          return result; // Return early, don't try to parse
        }
      }

      const lines = this.tcping_or_mtr_result.split("\n");

      for (const line of lines) {
        // Parse start time: "Start: Wed Jan 14 21:01:29 2026"
        if (line.startsWith("Start:")) {
          result.startTime = line.trim();
          continue;
        }

        // Parse host line: "HOST: PTT_BDG001          Loss%   Snt   Last   Avg  Best  Wrst StDev"
        if (line.includes("HOST:")) {
          const hostMatch = line.match(/HOST:\s*(\S+)/);
          if (hostMatch) {
            result.host = hostMatch[1];
          }
          continue;
        }

        // Parse hop lines - handles multiple formats:
        // New format: "  1.|-- AS4134 [CT] 202.97.43.62    0.0%    10    0.7   2.4   0.5  14.6   4.3"
        // New format: "  1.|-- AS4134 [CHINANET-BACKBONE China Telecom] 202.97.43.62    0.0%    10 ..."
        // Old format: "  1.|-- [CT] 202.97.43.62    0.0%    10 ..."
        // Private IP: "  1.|-- [Private] 192.168.1.1    0.0%    10 ..."
        // Lookup failed: "  1.|-- (IP) 59.43.152.145    0.0%    10 ..."

        const hopMatch = line.match(/^\s*(\d+)\.(?:\|--\s*|\s+)(.+)$/);
        if (hopMatch) {
          const hopNum = hopMatch[1];
          const restOfLine = hopMatch[2];

          let asNumber = ""; // AS number like "AS4134"
          let asn = ""; // AS name like "CT" or "CHINANET-BACKBONE"
          let ip = "";
          let ispName = "";
          let stats = [];

          // New format: AS##### [AS_NAME ...] IP stats
          // Example: AS4134 [CT] 202.97.43.62  or  AS4134 [CHINANET-BACKBONE China Telecom] 202.97.43.62
          const newFormatMatch = restOfLine.match(
            /^(AS\d+)\s+\[([^\]]+)\]\s+(\S+)\s+(.*)$/
          );
          if (newFormatMatch) {
            asNumber = newFormatMatch[1]; // AS4134
            const fullIspInfo = newFormatMatch[2]; // CT or CHINANET-BACKBONE China Telecom
            ip = newFormatMatch[3]; // 202.97.43.62
            stats = newFormatMatch[4].trim().split(/\s+/);

            // Split ISP info into AS name and ISP description
            const ispParts = fullIspInfo.split(" ", 1);
            asn = ispParts[0]; // CT or CHINANET-BACKBONE
            if (fullIspInfo.length > ispParts[0].length) {
              ispName = fullIspInfo.substring(ispParts[0].length).trim(); // Rest is ISP description
            }
          }
          // Old format with brackets but no AS number: [AS_NAME] IP stats
          else if (restOfLine.match(/^\[([^\]]+)\]\s+(.+)$/)) {
            const ispMatch = restOfLine.match(/^\[([^\]]+)\]\s+(.+)$/);
            const fullIspInfo = ispMatch[1];
            // Extract AS identifier - first word that's all caps/numbers/hyphens
            const asMatch = fullIspInfo.match(/^([A-Z0-9][A-Z0-9-]+)\s+(.+)$/i);
            if (asMatch) {
              asn = asMatch[1];
              ispName = asMatch[2].trim();
            } else {
              // Single word AS name like [CT] or [Private]
              asn = fullIspInfo.trim();
              ispName = "";
            }
            const afterIsp = ispMatch[2].trim().split(/\s+/);
            ip = afterIsp[0] || "";
            stats = afterIsp.slice(1);
          }
          // Format without brackets: (IP) 59.43.152.145 stats (lookup failed)
          else if (restOfLine.startsWith("(IP)")) {
            asn = "(IP)";
            const parts = restOfLine
              .replace("(IP)", "")
              .trim()
              .split(/\s+/);
            ip = parts[0] || "";
            stats = parts.slice(1);
          }
          // AS-prefixed hop without brackets: AS64497 198.18.1.1 stats (or AS??? IP stats)
          else {
            const parts = restOfLine.trim().split(/\s+/);
            if (parts[0] && parts[0].startsWith("AS")) {
              asNumber = parts[0];
              asn = parts[0];
              ip = parts[1] || "";
              stats = parts.slice(2);
            } else {
              ip = parts[0] || "";
              stats = parts.slice(1);
            }
          }

          // Extract numeric stats
          const numericStats = stats.filter(s => /^[\d.]+%?$/.test(s));

          // Map stats based on format
          // Local MTR: loss%, snt, last, avg, best, wrst, stdev
          let hopData = {
            num: hopNum,
            asNumber: asNumber, // AS number like "AS4134"
            asn: asn, // AS name like "CT" or "CHINANET-BACKBONE"
            ip: ip,
            ispName: ispName,
            loss: numericStats[0] || "",
            snt: "",
            last: "",
            avg: "",
            best: "",
            wrst: "",
            stdev: ""
          };

          // Local MTR columns: Loss%, Snt, Last, Avg, Best, Wrst, StDev
          hopData.snt = numericStats[1] || "";
          hopData.last = numericStats[2] || "";
          hopData.avg = numericStats[3] || "";
          hopData.best = numericStats[4] || "";
          hopData.wrst = numericStats[5] || "";
          hopData.stdev = numericStats[6] || "";

          result.hops.push(hopData);
          continue;
        }

        // Handle continuation lines (additional IPs for same hop)
        // "     AS???   104.254.113.198"
        const contMatch = line.match(/^\s+(AS\S*)\s+(\d+\.\d+\.\d+\.\d+)\s*$/);
        if (contMatch && result.hops.length > 0) {
          const lastHop = result.hops[result.hops.length - 1];
          // Append additional IP to existing hop
          lastHop.ip += ", " + contMatch[2];
        }
      }

      return result;
    },
    routeLoopInfo() {
      const result = { hasLoop: false, loopIps: [] };
      if (!this.parsedMtrData.hops || this.parsedMtrData.hops.length === 0) {
        return result;
      }

      // Count IP occurrences (ignore ??? and empty IPs)
      const ipCounts = {};
      for (const hop of this.parsedMtrData.hops) {
        const ip = hop.ip;
        if (!ip || ip === "???" || ip.includes("???")) continue;

        // Handle multiple IPs in the same hop (comma-separated)
        const ips = ip.split(",").map(s => s.trim());
        for (const singleIp of ips) {
          if (!singleIp || singleIp === "???") continue;
          ipCounts[singleIp] = (ipCounts[singleIp] || 0) + 1;
        }
      }

      // Find IPs that appear more than once
      for (const [ip, count] of Object.entries(ipCounts)) {
        if (count > 1) {
          result.hasLoop = true;
          result.loopIps.push(`${ip} (×${count})`);
        }
      }

      return result;
    },
    resultClass() {
      if (this.is_dns_error) return "red lighten-4";

      const result = this.tcping_or_mtr_result;
      if (!result) return "";

      // Check for connection error
      if (
        result.includes("cannot tcping to port 52770") ||
        result.includes("SSH connection aborted") ||
        result.includes("error:") ||
        result.includes("Cannot resolve host") ||
        result.includes("Failed to resolve host") ||
        result.includes("upstream request timeout") ||
        result.includes("API rejected") ||
        result.includes("measurement timed out") ||
        result.includes("probe may be offline")
      ) {
        return "red lighten-4";
      }

      // Check for packet loss via Summary
      // Pattern: Failed=X (Y.YY%)
      const match = result.match(/Failed=\d+\s+\((\d+\.\d+)%\)/);
      if (match) {
        const lossPercentage = parseFloat(match[1]);
        if (lossPercentage === 100.0) {
          return "red lighten-4";
        } else if (lossPercentage > 0) {
          return "yellow lighten-2";
        } else {
          return "green lighten-2";
        }
      }

      // Fallback: Check for "Connection time out" strings if summary is not yet available or parsed
      const hasTimeout =
        result.includes("Connection time out") ||
        result.includes("Connection timed out");
      const hasSuccess =
        result.includes("latency=") || result.includes("time=");

      if (hasTimeout) {
        if (!hasSuccess) {
          return "red lighten-4";
        } else {
          return "yellow lighten-2";
        }
      }

      // Check if MTR completed successfully
      if (result.includes("---MTR_COMPLETE---")) {
        return "green lighten-2";
      }

      // Default to white while still running
      return "white";
    }
  },
  watch: {
    probe_ip: {
      handler() {
        this.is_dns_error = false;
      }
    },
    tcping_or_mtr_result: {
      handler(newVal) {
        // Reset error state when result is cleared (new test starting)
        if (!newVal) {
          this.is_dns_error = false;
          return;
        }

        let status = "success";
        this.is_dns_error = false;

        // Check for SSH/Connection errors (Strict)
        if (
          newVal.includes("cannot tcping to port 52770") ||
          newVal.includes("SSH connection aborted")
        ) {
          status = "connection_error";
        } else {
          // Check for DNS resolution issues in the output
          if (newVal.includes("127.0.0.1") && newVal.includes("PING")) {
            status = "dns_error";
            this.is_dns_error = true;
          } else if (
            newVal.includes("unknown host") ||
            newVal.includes("Name or service not known") ||
            newVal.includes("Failed to resolve host")
          ) {
            status = "dns_error";
            this.is_dns_error = true;
          }
        }

        this.$emit("dns-resolution-status", {
          ip: this.probe_ip,
          hostname: this.linux_hostname,
          status: status,
          isp: this.isp
        });
      }
    }
  }
};
</script>

<style>
#pre_text_tcp_trace_route {
  height: auto;
  max-height: 400px;
  overflow: auto;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.mtr-table-container {
  padding: 8px;
}

.mtr-header {
  padding: 6px 12px;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-radius: 6px;
  border-left: 4px solid #1976d2;
}

.mtr-table {
  font-size: 12px !important;
  border-radius: 6px;
  overflow: hidden;
}

.mtr-table th {
  font-size: 11px !important;
  padding: 6px 8px !important;
  white-space: nowrap;
  color: #37474f;
  font-weight: 600;
}

.mtr-table td {
  font-size: 12px !important;
  padding: 4px 8px !important;
  font-family: "Roboto Mono", monospace;
}

.mtr-table tbody tr:hover {
  background-color: #e3f2fd !important;
}

.mtr-table tbody tr {
  border-bottom: 1px solid #eceff1;
}

.error-container {
  background: #ffebee;
  border-radius: 8px;
}
</style>
