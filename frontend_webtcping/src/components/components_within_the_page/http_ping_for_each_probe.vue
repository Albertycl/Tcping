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
      isUpdatingIp: false
    };
  },

  updated() {
    this.scrollToEnd();
  },
  methods: {
    scrollToEnd() {
      var container = this.$el.querySelector("#pre_text");
      console.log(`container=${container}`);
      container.scrollTop = container.scrollHeight;
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
          console.log(this.probe_ip);
          axios
            .get(
              `/api/e01_http_ping/${this.getting_the_ip_or_url_from_vuex}/${this.probe_ip}/${this.getting_the_port_from_vuex}`
            )
            .then((response) => {
              // console.log(`${this.probe_ip} / response=${response.data}`);
              let file_name = response.data;
              if (typeof file_name === 'string' && (file_name.includes("Exception") || file_name.includes("error"))) {
                  this.tcping_or_mtr_result = file_name;
                  this.$emit("probe-complete", this.probe_ip);
                  return;
              }
              // Smarter polling with completion detection
              let attempts = 0;
              const maxAttempts = 9;
              const poll = () => {
                if (attempts >= maxAttempts) {
                  this.how_many_times_will_set_interval_be_triggered = 0;
                  this.$emit("probe-complete", this.probe_ip);
                  return;
                }
                const delay = attempts < 3 ? 1500 : Math.min(1500 * Math.pow(1.3, attempts - 3), 4000);

                setTimeout(() => {
                  axios.get(`/api/a02_opening_apache_on_golden_eye_server/${file_name}/${this.probe_ip}`)
                    .then((response) => {
                      this.tcping_or_mtr_result = response.data;
                      attempts++;
                      this.how_many_times_will_set_interval_be_triggered = attempts;

                      if (response.data.includes("error") ||
                          response.data.includes("404") ||
                          response.data.includes("HTTP/") ||
                          response.data.includes("avg:")) {
                        this.how_many_times_will_set_interval_be_triggered = 0;
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