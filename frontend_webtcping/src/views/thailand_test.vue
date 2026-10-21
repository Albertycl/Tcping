<template>
  <div class="thailand-test-container">
    <h2 class="page-title">Thailand Probes Test - www.example.com</h2>

    <!-- Loading indicator -->
    <v-progress-circular
      v-if="loading || is_any_probe_polling"
      indeterminate
      color="primary"
      class="mb-4"
    ></v-progress-circular>
    <span v-if="loading" class="ml-2">Loading probes...</span>
    <span v-else-if="is_any_probe_polling" class="ml-2">Tests in progress...</span>

    <!-- Error Alert -->
    <v-alert
      v-if="error_message"
      type="error"
      dense
      outlined
      class="mt-2 mb-2"
    >
      {{ error_message }}
    </v-alert>

    <!-- Results Grid - 3 columns per probe row -->
    <div v-for="(probe, index) in list_th_probes" :key="`${probe.server_ip}-${index}`" class="probe-row">
      <!-- Header row with probe info -->
      <div class="probe-header">
        <span class="probe-name">{{ probe.isp }}_{{ probe.which_city }}</span>
        <span class="probe-ip">{{ probe.server_ip }}</span>
      </div>

      <v-row class="probe-results">
        <!-- TCPING Column -->
        <v-col cols="4">
          <v-card class="pa-2 result-card">
            <div class="column-header tcping-header">TCPING</div>
            <tcping_for_each_probe
              :probe_ip="probe.server_ip"
              :linux_hostname="probe.which_city"
              :linux_public_ip="probe.linux_public_ip"
              :isp_name="probe.isp"
              storeKey="tcping"
              @dns-resolution-status="handle_dns_status"
              @polling-status="handle_polling_status"
            ></tcping_for_each_probe>
          </v-card>
        </v-col>

        <!-- TCP_TRACE Column -->
        <v-col cols="4">
          <v-card class="pa-2 result-card">
            <div class="column-header tcptrace-header">TCP_TRACE</div>
            <tcp_trace_for_each_probe
              :probe_ip="probe.server_ip"
              :linux_hostname="probe.which_city"
              :linux_public_ip="probe.linux_public_ip"
              :isp_name="probe.isp"
              storeKey="mtr"
              @dns-resolution-status="handle_dns_status"
            ></tcp_trace_for_each_probe>
          </v-card>
        </v-col>

        <!-- CURL Column -->
        <v-col cols="4">
          <v-card class="pa-2 result-card">
            <div class="column-header curl-header">CURL</div>
            <curl_for_each_probe
              :probe_ip="probe.server_ip"
              :linux_hostname="probe.which_city"
              :linux_public_ip="probe.linux_public_ip"
              :isp_name="probe.isp"
              country_code="TH"
              @dns-resolution-status="handle_dns_status"
            ></curl_for_each_probe>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- Summary section for API consumption -->
    <div v-if="all_tests_complete" class="summary-section mt-4">
      <h3>Test Summary</h3>
      <pre class="summary-data">{{ JSON.stringify(getSummaryData(), null, 2) }}</pre>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import tcping_for_each_probe from "@/components/components_within_the_page/tcping_for_each_probe.vue";
import tcp_trace_for_each_probe from "@/components/components_within_the_page/tcp_trace_for_each_probe.vue";
import curl_for_each_probe from "@/components/components_within_the_page/curl_for_each_probe.vue";

export default {
  name: "ThailandTest",
  components: {
    tcping_for_each_probe,
    tcp_trace_for_each_probe,
    curl_for_each_probe
  },
  data() {
    return {
      target_url: "www.example.com",
      target_port: 443,
      list_th_probes: [],
      loading: true,
      error_message: "",
      active_polling_probes: new Set(),
      dns_probes_tracked: new Set(),
      all_tests_complete: false
    };
  },
  computed: {
    is_any_probe_polling() {
      return this.active_polling_probes.size > 0;
    }
  },
  async mounted() {
    await this.fetchThailandProbes();
    if (this.list_th_probes.length > 0) {
      await this.startAllTests();
    }
  },
  methods: {
    async fetchThailandProbes() {
      this.loading = true;
      this.error_message = "";
      try {
        const response = await axios.get(
          "/api/axios_show_which_host_isp_for_webpaping/TH"
        );
        this.list_th_probes = response.data;
        if (!this.list_th_probes.length) this.error_message = "No probes are configured for TH";
        console.log(`Loaded ${this.list_th_probes.length} Thailand probes`);
      } catch (error) {
        console.error("Failed to fetch Thailand probes:", error);
        this.error_message = `Failed to fetch probes: ${error.message}`;
      } finally {
        this.loading = false;
      }
    },

    async startAllTests() {
      this.error_message = "";
      const probeIps = this.list_th_probes.map(p => p.server_ip);

      // Mark all probes as polling
      probeIps.forEach(ip => this.active_polling_probes.add(ip));
      this.active_polling_probes = new Set(this.active_polling_probes);

      // Reset probe results
      this.$store.commit("resetTcpingProbeResults");
      this.$store.commit("resetMtrProbeResults");
      this.$store.commit("setTcpingBatchInProgress", true);
      this.$store.commit("setMtrBatchInProgress", true);

      // Trigger curl via Vuex
      this.$store.commit("passing_in_the_payload", {
        key_ip_or_url_for_tcping: "https://" + this.target_url,
        key_port_for_tcping: "HTTP1.1",
        key_tls_12_or_tls13: "1.2",
        key_ip_for_the_hostfile: "",
        key_url_for_the_hostfile: ""
      });

      // Run TCPING and MTR batch SSE in parallel
      try {
        await Promise.all([
          this.runTcpingBatch(probeIps),
          this.runMtrBatch(probeIps)
        ]);
      } catch (error) {
        console.error("Batch SSE error:", error);
        this.error_message = `Test error: ${error.message}`;
      } finally {
        this.$store.commit("setTcpingBatchInProgress", false);
        this.$store.commit("setMtrBatchInProgress", false);
        this.active_polling_probes = new Set();
        this.all_tests_complete = true;

        // Reset curl trigger after delay
        setTimeout(() => {
          this.$store.commit("passing_in_the_payload", {
            key_ip_or_url_for_tcping: "",
            key_port_for_tcping: ""
          });
        }, 15000);
      }
    },

    async runTcpingBatch(probeIps) {
      const response = await fetch(
        "/api/sse/batch/tcping",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target: this.target_url,
            port: this.target_port,
            count: 20,
            probes: probeIps
          })
        }
      );

      if (!response.ok) {
        throw new Error(`TCPING server returned ${response.status}: ${(await response.text()).slice(0, 300)}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // eslint-disable-next-line no-constant-condition
      readLoop: while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const json = JSON.parse(line.slice(6));
              if (json.heartbeat) continue;
              if (json.all_complete) break readLoop;

              this.$store.commit("updateTcpingProbeResult", {
                probe_ip: json.probe_ip,
                data: json.data,
                complete: json.complete
              });

              if (json.complete) {
                this.active_polling_probes.delete(json.probe_ip);
                this.active_polling_probes = new Set(this.active_polling_probes);
              }
            } catch (e) {
              console.log("Failed to parse TCPING SSE data:", line, e);
            }
          }
        }
      }
    },

    async runMtrBatch(probeIps) {
      const response = await fetch(
        "/api/sse/batch/mtr",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target: this.target_url,
            port: this.target_port,
            probes: probeIps
          })
        }
      );

      if (!response.ok) {
        throw new Error(`MTR server returned ${response.status}: ${(await response.text()).slice(0, 300)}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // eslint-disable-next-line no-constant-condition
      readLoop: while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const json = JSON.parse(line.slice(6));
              if (json.heartbeat) continue;
              if (json.all_complete) break readLoop;

              this.$store.commit("updateMtrProbeResult", {
                probe_ip: json.probe_ip,
                data: json.data,
                complete: json.complete
              });
            } catch (e) {
              console.log("Failed to parse MTR SSE data:", line, e);
            }
          }
        }
      }
    },

    handle_dns_status(status) {
      if (!this.dns_probes_tracked.has(status.ip)) {
        this.dns_probes_tracked.add(status.ip);
      }
    },

    handle_polling_status(status) {
      if (status.polling) {
        this.active_polling_probes.add(status.ip);
      } else {
        this.active_polling_probes.delete(status.ip);
      }
      this.active_polling_probes = new Set(this.active_polling_probes);
    },

    getSummaryData() {
      const tcpingResults = this.$store.state.tcpingProbeResults;
      const mtrResults = this.$store.state.mtrProbeResults;

      return {
        target: this.target_url,
        port: this.target_port,
        timestamp: new Date().toISOString(),
        probes: this.list_th_probes.map(probe => ({
          probe_id: probe.server_ip,
          location: probe.which_city,
          isp: probe.isp,
          tcping: tcpingResults[probe.server_ip] || null,
          mtr: mtrResults[probe.server_ip] || null
        }))
      };
    }
  }
};
</script>

<style scoped>
.thailand-test-container {
  padding: 16px;
  max-width: 100%;
}

.page-title {
  color: #1976d2;
  margin-bottom: 16px;
  font-size: 1.5rem;
}

.probe-row {
  margin-bottom: 16px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 16px;
}

.probe-header {
  margin-bottom: 8px;
}

.probe-name {
  font-weight: bold;
  font-size: 1.1rem;
  color: #1565c0;
}

.probe-ip {
  margin-left: 12px;
  color: #757575;
  font-size: 0.85rem;
}

.result-card {
  height: 100%;
  min-height: 200px;
}

.column-header {
  font-weight: bold;
  font-size: 0.85rem;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 2px solid;
}

.tcping-header {
  color: #1976d2;
  border-color: #1976d2;
}

.tcptrace-header {
  color: #388e3c;
  border-color: #388e3c;
}

.curl-header {
  color: #f57c00;
  border-color: #f57c00;
}

.summary-section {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
}

.summary-data {
  background: #263238;
  color: #aed581;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.8rem;
}
</style>
