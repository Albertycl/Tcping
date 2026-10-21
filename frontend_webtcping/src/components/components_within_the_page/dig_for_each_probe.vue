<template>
  <div :class="{'red lighten-4': is_dns_error}">
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
      <span class="blue--text text--darken-3 font-weight-medium">{{ isp_name }}_{{ linux_hostname }}_{{ probe_ip }}</span> /
      <span class="cyan lighten-4 pa-1 rounded text-h6 blue--text text--darken-2">public ip:{{ linux_public_ip }}</span>
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
    <div id="pre_text">
      <pre class="light-blue lighten-5">{{ tcping_or_mtr_result }}</pre>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  props: ["probe_ip", "probe_id", "linux_hostname", "linux_public_ip", "isp_name"],
  data() {
    return {
      how_many_times_will_set_interval_be_triggered: 0,
      tcping_or_mtr_result: "",
      is_dns_error: false,
      eventSource: null,
      isUpdatingIp: false
    };
  },

  updated() {
    this.scrollToEnd();
  },
  beforeDestroy() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  },
  methods: {
    scrollToEnd() {
      var container = this.$el.querySelector("#pre_text");
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
    startSSE() {
      if (this.eventSource) {
        this.eventSource.close();
      }

      const sseUrl = `/api/sse/dig/${this.getting_the_ip_or_url_from_vuex}/${this.probe_ip}`;
      console.log(`[${this.probe_ip}] Starting DIG SSE connection: ${sseUrl}`);

      this.eventSource = new EventSource(sseUrl);

      this.eventSource.onmessage = (event) => {
        const data = event.data.replace(/\\n/g, '\n');
        // Remove completion marker from display
        this.tcping_or_mtr_result = data.replace("---DIG_COMPLETE---", "").trim();
        this.how_many_times_will_set_interval_be_triggered++;

        // Check for completion marker or fallback patterns
        if (data.includes("---DIG_COMPLETE---") || data.includes("Query time:") || data.startsWith("error")) {
          this.eventSource.close();
          this.eventSource = null;
          this.$emit("probe-complete", this.probe_ip);
        }
      };

      this.eventSource.onerror = (error) => {
        console.log(`[${this.probe_ip}] SSE error:`, error);
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }
        this.$emit("probe-complete", this.probe_ip);
      };
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
        const errorMsg = error.response?.data?.error || error.message || "Unknown error";
        alert(`Error: ${errorMsg}`);
      } finally {
        this.isUpdatingIp = false;
      }
    }
  },

  computed: {
    getting_the_ip_or_url_from_vuex() {
      return this.$store.state.vuex_ip_or_url_for_tcping;
    },
    getting_the_port_from_vuex() {
      return this.$store.state.vuex_port_for_tcping;
    },
  },
  watch: {
    probe_ip: {
      handler() {
        this.tcping_or_mtr_result = "";
        this.is_dns_error = false;
      },
    },
    getting_the_ip_or_url_from_vuex: {
      handler() {
        if (this.getting_the_ip_or_url_from_vuex != "") {
          this.tcping_or_mtr_result = "";
          this.how_many_times_will_set_interval_be_triggered = 0;
          console.log(this.probe_ip);

          // Use SSE instead of polling
          this.startSSE();
        }
      },
    },
    tcping_or_mtr_result: {
        handler(newVal) {
            // Reset error state when result is cleared (new test starting)
            if (!newVal) {
                this.is_dns_error = false;
                return;
            }

              let status = 'success';
              this.is_dns_error = false;

              // Check for SSH/Connection errors (Strict)
              if (newVal.includes("cannot tcping to port 52770") || newVal.includes("SSH connection aborted")) {
                  status = 'connection_error';
              } else {
                  // Check for DNS resolution issues in the output
                  if (newVal.includes("127.0.0.1") && newVal.includes("PING")) {
                      status = 'dns_error';
                      this.is_dns_error = true;
                  } else if (newVal.includes("unknown host") || newVal.includes("Name or service not known")) {
                      status = 'dns_error';
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
  },

};
</script>

<style>
#pre_text {
  height: auto;
  max-height: 200px;
  overflow: auto;
  /*overflow-y: none;*/
  background-color: #eeeeee;
}
</style>