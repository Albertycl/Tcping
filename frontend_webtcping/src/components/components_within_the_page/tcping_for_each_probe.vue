<template>
  <div :class="resultClass">
    <!-- how_many_times_will_set_interval_be_triggered = -->
    <!-- {{ how_many_times_will_set_interval_be_triggered }} -->
    <!-- <p class="green">{{ getting_the_ip_or_url_from_vuex }}</p> -->
    <!-- <p class="blue">{{ getting_the_port_from_vuex }}</p> -->
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
    <div :class="['pre_text', tallMode ? 'tall-mode' : '']">
      <pre :class="resultClass">{{ tcping_or_mtr_result }}</pre>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  props: ["probe_ip", "probe_id", "linux_hostname", "linux_public_ip", "isp_name", "storeKey", "tallMode"],
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
      var container = this.$el.querySelector(".pre_text");
      console.log(`container=${container}`);
      if (container) container.scrollTop = container.scrollHeight;
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
        const errorMsg = error.response?.data?.error || error.message || "Unknown error";
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
      if (this.storeKey === "tcping") {
        return this.$store.state.tcpingProbeResults[this.probe_ip] || "";
      }
      return this.$store.state.probeResults[this.probe_ip] || "";
    },
    isComplete() {
      if (this.storeKey === "tcping") {
        return this.$store.state.tcpingProbeCompleted[this.probe_ip] || false;
      }
      return this.$store.state.probeCompleted[this.probe_ip] || false;
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
          // If there are timeouts and NO success indicators, assume total failure (Red)
          // But be careful: if it just started and failed the first one, it might be too early to call it total failure?
          // User said "if totally connection time out change the bg to red".
          // If we have at least one timeout and NO success, it's bad.
          // However, if the output is just "Connection time out" (one line), it's 100% loss so far.
          return "red lighten-4";
        } else {
          // Mixed results (Yellow)
          return "yellow lighten-2";
        }
      }

      // Default to green if no specific error/loss detected but result exists
      return "green lighten-2";
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
            newVal.includes("Cannot resolve host")
          ) {
            status = "dns_error";
            this.is_dns_error = true;
          }
        }

        this.$emit("dns-resolution-status", {
          ip: this.probe_ip,
          hostname: this.linux_hostname,
          status: status
        });
      }
    }
  }
};
</script>

<style>
.pre_text {
  height: auto;
  max-height: 200px;
  overflow: auto;
  background-color: #eeeeee;
}

.pre_text.tall-mode {
  max-height: 400px;
}
</style>
