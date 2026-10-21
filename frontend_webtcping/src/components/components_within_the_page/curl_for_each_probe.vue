<template>
  <div class="pl-4" :class="{
    'red lighten-4': has_result && (!is_whitelist_match || is_dns_error || is_connection_error) && !is_ltm_config_match,
    'green lighten-4': has_result && (is_whitelist_match || is_ltm_config_match) && !is_dns_error && !is_connection_error,
    'white': !has_result
  }">
    <!-- how_many_times_will_set_interval_be_triggered = -->
    <!-- {{ how_many_times_will_set_interval_be_triggered }} -->
    <!-- <p class="green">{{ getting_the_ip_or_url_from_vuex }}</p> -->
    <!-- <p class="blue">{{ getting_the_port_from_vuex }}</p> -->
    {{ getting_the_ip_for_hostfile_from_vuex }}
    {{ getting_the_url_for_hostfile_from_vuex }}
    {{ getting_the_tls_version_from_vuex }}
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
    <p v-if="has_result && status_reason" class="font-weight-bold text-caption">
      <span :class="is_whitelist_match && !is_dns_error && !is_connection_error ? 'green--text' : 'red--text'">
        {{ is_dns_error ? 'DNS Error' : status_reason }}
      </span>
    </p>
    <!-- LTM Config Check Result -->
    <div v-if="ltm_config_result" class="text-caption mt-1">
      <span v-if="ltm_config_result.status === 'success'" class="green--text font-weight-bold">
        <v-icon small color="green">mdi-check-circle</v-icon>
        LTM Config Match:
        <span v-for="(mc, idx) in ltm_config_result.matched_cookies" :key="idx" class="ml-1">
          {{ mc.cookie.cookie_name }}={{ mc.cookie.ip_reversed }}
        </span>
      </span>
      <span v-else-if="ltm_config_result.status === 'failure'" class="orange--text">
        <v-icon small color="orange">mdi-alert</v-icon>
        {{ ltm_config_result.message }}
      </span>
      <span v-else-if="ltm_config_result.status === 'no_cookie'" class="grey--text">
        No F5 BigIP cookie detected
      </span>
      <!-- Show unmatched cookies if any -->
      <div v-if="ltm_config_result.unmatched_cookies && ltm_config_result.unmatched_cookies.length > 0" class="mt-1 orange--text" style="font-size: 10px;">
        <v-icon x-small color="orange">mdi-alert</v-icon>
        Not in config:
        <span v-for="(uc, idx) in ltm_config_result.unmatched_cookies" :key="idx" class="ml-1">
          {{ uc.cookie_name }}={{ uc.ip_reversed }}
        </span>
      </div>
      <div v-if="ltm_config_result.available_files && ltm_config_result.available_files.length > 0" class="mt-1 grey--text text--darken-1" style="font-size: 10px;">
        Config files checked:
        <a v-for="(url, idx) in ltm_config_result.available_files" :key="idx"
           :href="url" target="_blank" class="ml-1 blue--text">
          {{ url.includes('Alpha') ? 'Alpha' : 'Bravo' }}_{{ url.match(/\d{8}/)?.[0] || '' }}
        </a>
      </div>
    </div>
    <div :class="['curl_result_area', tallMode ? 'tall-mode' : '']">
      <pre>{{ tcping_or_mtr_result }}</pre>
    </div>
  </div>
</template>

<script>
import axios from "axios";
export default {
  props: ["probe_ip", "probe_id", "linux_hostname", "linux_public_ip", "isp_name", "country_code", "tallMode"],
  data() {
    return {
      how_many_times_will_set_interval_be_triggered: 0,
      tcping_or_mtr_result: "",
      is_dns_error: false,
      is_whitelist_match: false,
      has_result: false,
      status_reason: "",
      is_connection_error: false,
      isUpdatingIp: false,
      ltm_config_result: null
    };
  },

  updated() {
    this.scrollToEnd();
  },
  methods: {
    scrollToEnd() {
      var container = this.$el.querySelector(".curl_result_area");
      console.log(`container=${container}`);
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },
    copyToClipboard(text) {
      var dummy = document.createElement("textarea");
      console.log("***************************dummy=" + dummy);
      document.body.appendChild(dummy);
      dummy.value = text;
      dummy.select();
      document.execCommand("copy");
      try {
        var successful = document.execCommand("copy");
        var msg = successful ? "successful" : "unsuccessful";
        alert(this.tcping_or_mtr_result + " was copied " + msg);
      } catch (err) {
        alert("Oops, unable to copy");
      }
      document.body.removeChild(dummy);
    }, //end of copyToClipboard
    checkWhitelist(content) {
        // Skip if waiting for result
        if (content === "Waiting for result...") {
            this.has_result = false;
            return;
        }

        this.has_result = true;
        this.is_connection_error = false;
        this.is_dns_error = false;

        // Check if probe is working: port 52770 reachable + got HTTP response
        const hasHttpResponse = content.includes("HTTP/") ||
                                content.includes("Server:") ||
                                content.includes("Content-Type:");

        // Probe connection error ONLY if: no HTTP response AND probe connectivity failed
        if (!hasHttpResponse) {
            if ((content.includes("Port 52770") && content.includes("not reachable")) ||
                content.includes("cannot tcping to port 52770") ||
                content.includes("SSH connection aborted")) {
                this.is_connection_error = true;
                this.is_whitelist_match = false;
                this.status_reason = "Probe connection error";
                return;
            }
        }

        // If we have HTTP response, probe is working - proceed to whitelist check
        // All curl errors (SSL, connection, ISP block) are handled by whitelist API

          let status = 'success';

          // Check for DNS resolution issues in the output
          if (content.includes("127.0.0.1") && content.includes("PING")) {
              status = 'dns_error';
              this.is_dns_error = true;
          } else if (content.includes("unknown host") || content.includes("Name or service not known")) {
              status = 'dns_error';
              this.is_dns_error = true;
          }

          this.$emit("dns-resolution-status", {
              ip: this.probe_ip,
              hostname: this.linux_hostname,
              status: status
          });

        // Extract only the curl output for whitelist checking (exclude ping section)
        let contentForWhitelist = content;

        // Look for the separator line between ping and curl sections
        const separatorIndex = content.indexOf('=============================================================');
        if (separatorIndex !== -1) {
            // Take everything after the separator line
            contentForWhitelist = content.substring(separatorIndex).trim();
        } else {
            // Fallback: look for curl progress output markers
            const curlProgressIndex = content.indexOf('% Total');
            if (curlProgressIndex !== -1) {
                contentForWhitelist = content.substring(curlProgressIndex).trim();
            }
        }

        // Note: do NOT truncate at HTTP/ since response headers (Location, Set-Cookie, etc.)
        // may appear before the HTTP status line and contain whitelist-matching patterns

        // Check whitelist via API
        axios.post('/api/api/check_whitelist', {
            content: contentForWhitelist,
            country: this.country_code
        })
            .then(response => {
                if (response.data.status === 'success') {
                    this.is_whitelist_match = true;
                    const matched = response.data.matched_condition;
                    this.status_reason = matched ? `Matched: ${matched.condition_name || matched.condition_pattern}` : "Whitelist matched";
                } else {
                    this.is_whitelist_match = false;
                    if (response.data.matched_condition) {
                        const matched = response.data.matched_condition;
                        this.status_reason = `Blocked: ${matched.condition_name || matched.condition_pattern}`;
                    } else {
                        this.status_reason = response.data.reason || "No whitelist match";
                    }
                }
            })
            .catch(e => {
                console.error("Whitelist check failed:", e);
                this.status_reason = "Whitelist check failed";
            });

        // Also check LTM config files for server IP from oneapi cookie
        axios.post('/api/api/check_ltm_config', {
            content: content
        })
            .then(response => {
                this.ltm_config_result = response.data;
            })
            .catch(e => {
                console.error("LTM config check failed:", e);
                this.ltm_config_result = null;
            });
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
    getting_the_ip_for_hostfile_from_vuex() {
      return this.$store.state.vuex_ip_for_hostfile;
    },
    getting_the_url_for_hostfile_from_vuex() {
      return this.$store.state.vuex_url_for_hostfile;
    },
    getting_the_tls_version_from_vuex() {
      return this.$store.state.vuex_tls_12_or_tls13;
    },
    is_ltm_config_match() {
      return this.ltm_config_result && this.ltm_config_result.status === 'success';
    },
  },
  watch: {
    probe_ip: {
      handler() {
        this.tcping_or_mtr_result = "";
        this.is_dns_error = false;
        this.is_connection_error = false;
        this.status_reason = "";
        this.has_result = false;
        this.is_whitelist_match = false;
        this.ltm_config_result = null;
      },
    },
    getting_the_ip_or_url_from_vuex: {
      immediate: true,
      handler(newVal) {
        // Only run if it's a valid URL (not default/empty) and we have probe_ip
        const isValidUrl =
          newVal &&
          newVal !== "" &&
          newVal !== "from_vuex_default_url" &&
          newVal.startsWith("http");
        if (isValidUrl && this.probe_ip) {
          this.tcping_or_mtr_result = "";
          this.status_reason = "";
          this.has_result = false;
          this.is_whitelist_match = false;
          this.is_dns_error = false;
          this.is_connection_error = false;
          this.ltm_config_result = null;
          console.log(this.probe_ip);
          axios
            .post("/api/d01_do_curl_to_ge_probes/", {
              getting_the_ip_or_url_from_vuex: this.getting_the_ip_or_url_from_vuex,
              probe_ip: this.probe_ip,
              ip_for_hostfile_from_vuex: this.getting_the_ip_for_hostfile_from_vuex,
              url_for_hostfile_from_vuex: this.getting_the_url_for_hostfile_from_vuex,
              getting_the_port_from_vuex: this.getting_the_port_from_vuex,
              getting_the_tls_version_from_vuex: this.getting_the_tls_version_from_vuex,
            })
            .then((response) => {
              // console.log(`${this.probe_ip} / response=${response.data}`);
              let file_name = response.data;
              // Check for error responses (SSH failures, connection errors, etc.)
              if (typeof file_name === 'string' && (
                  file_name.includes("Exception") ||
                  file_name.includes("error") ||
                  file_name.includes("not reachable") ||
                  file_name.includes("SSH connection") ||
                  file_name.includes("timed out")
              )) {
                  this.tcping_or_mtr_result = file_name;
                  this.checkWhitelist(file_name);
                  this.$emit("probe-complete", this.probe_ip);
                  return;
              }
              // Smarter polling with completion detection
              let attempts = 0;
              const maxAttempts = 8; // Reduced from 10 for faster completion
              const poll = () => {
                if (attempts >= maxAttempts) {
                  this.how_many_times_will_set_interval_be_triggered = 0;
                  if (this.tcping_or_mtr_result && this.tcping_or_mtr_result !== "Waiting for result...") {
                    this.checkWhitelist(this.tcping_or_mtr_result);
                  }
                  this.$emit("probe-complete", this.probe_ip);
                  return;
                }
                const delay = attempts < 2 ? 1500 : Math.min(2000 * Math.pow(1.2, attempts - 2), 3500);

                setTimeout(() => {
                  axios.get(`/api/a02_opening_apache_on_golden_eye_server/${file_name}/${this.probe_ip}`)
                    .then((response) => {
                      const data = response.data ? response.data.toString() : "";
                      if (!data || data.trim() === "") {
                        this.tcping_or_mtr_result = "Waiting for result...";
                      } else {
                        this.tcping_or_mtr_result = data;
                      }
                      attempts++;
                      this.how_many_times_will_set_interval_be_triggered = attempts;

                      // Check for curl completion indicators
                      const isComplete = data.includes("HTTP/") ||
                          data.includes("curl:") ||
                          data.includes("error") ||
                          data.includes("404") ||
                          data.includes("Content-Type:") ||
                          data.includes("Content-Length:") ||
                          data.includes("Connection:") ||
                          data.includes("Server:") ||
                          data.includes("Date:") ||
                          data.includes("Location:") ||
                          data.includes("SSL routines") ||
                          data.includes("Could not resolve") ||
                          data.includes("Connection refused") ||
                          data.includes("timed out");

                      if (isComplete) {
                        this.how_many_times_will_set_interval_be_triggered = 0;
                        this.checkWhitelist(this.tcping_or_mtr_result);
                        this.$emit("probe-complete", this.probe_ip);
                        return;
                      }
                      poll();
                    })
                    .catch((error) => {
                      console.log(error);
                      this.how_many_times_will_set_interval_be_triggered = 0;
                      this.$emit("probe-complete", this.probe_ip);
                    });
                }, delay);
              };
              poll();
            })
            .catch((error) => {
              console.log(error);
              this.$emit("probe-complete", this.probe_ip);
            });
        }
      },
    },
    tcping_or_mtr_result: {
        handler(newVal) {
            // Reset state when result is cleared (new test starting)
            if (!newVal) {
                this.is_dns_error = false;
                this.is_connection_error = false;
                this.has_result = false;
                this.is_whitelist_match = false;
                return;
            }
            // checkWhitelist is called directly from polling completion, not here
        }
    }
  },
};
</script>

<style>
.curl_result_area {
  height: auto;
  max-height: 200px;
  overflow: auto;
}

.curl_result_area.tall-mode {
  max-height: 400px;
}
</style>