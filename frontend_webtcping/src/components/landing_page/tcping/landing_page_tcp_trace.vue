<template>
  <div>
    <nav_bar_for_tcping_and_tcp_trace></nav_bar_for_tcping_and_tcp_trace>
    <v-row class="mt-2" v-if="after_starting_tcping_or_mtr_hide_the_input_row">
      <v-col>
        <p class="font-weight-medium">
          choose ISP for TCP Trace
        </p>
        <v-btn @click="get_ct_probe_ip('CT')">CT</v-btn>
        <v-btn @click="get_ct_probe_ip('CU')">CU</v-btn>
        <v-btn @click="get_ct_probe_ip('CM')">CM</v-btn>
        <v-btn @click="get_ct_probe_ip('VN')">VN</v-btn>
        <v-btn @click="get_ct_probe_ip('INDO')">INDO</v-btn>
        <v-btn @click="get_ct_probe_ip('Malaysia')">Malaysia</v-btn>
        <v-btn @click="get_ct_probe_ip('Cambodia')">Cambodia</v-btn>
        <v-btn @click="get_ct_probe_ip('TH')">TH</v-btn>
        <v-btn @click="get_ct_probe_ip('KR')">KR</v-btn>
        <v-btn @click="get_all_the_probes()">customize</v-btn>
      </v-col>
    </v-row>

    <!-- Error Alert -->
    <v-alert
      v-if="error_message"
      type="error"
      dense
      outlined
      dismissible
      class="mt-2 mb-2"
      @input="error_message = ''"
    >
      {{ error_message }}
    </v-alert>

    <!-- DNS Summary Alert -->
    <v-alert
      v-if="dns_summary.total > 0"
      :type="
        dns_summary.dns_poisoned > 0 || dns_summary.ssh_failed > 0
          ? 'warning'
          : 'success'
      "
      dense
      outlined
      class="mt-2"
    >
      <div>
        <strong>DNS Resolution Summary:</strong>
        {{ dns_summary.dns_poisoned }} / {{ dns_summary.total }} local probes
        failed to resolve target (127.0.0.1 or unknown host).
      </div>
      <div
        v-if="dns_summary.dns_poisoned_probes.length > 0"
        class="mt-1 text-caption red--text"
      >
        <strong>DNS Poisoning Detected:</strong>
        {{ dns_summary.dns_poisoned_probes.join(", ") }}
      </div>
      <div
        v-if="dns_summary.ssh_failed > 0"
        class="mt-1 text-caption orange--text"
      >
        <strong>SSH Connection Failed (Excluded from Total):</strong>
        {{ dns_summary.ssh_failed_probes.join(", ") }}
      </div>
    </v-alert>

    <!-- Grouped Chip Grid Layout -->
    <div v-if="hide_the_panel" class="mt-2 pa-3 grey lighten-4 rounded">
      <div class="d-flex justify-space-between align-center mb-3">
        <span class="text-subtitle-2 grey--text text--darken-1"
          >Selected:
          {{ vuex_all_the_probes_that_is_selected.length }} probes</span
        >
        <div>
          <v-btn
            x-small
            text
            color="primary"
            @click="selectAllProbes"
            class="mr-2"
            >Select All</v-btn
          >
          <v-btn x-small text color="grey" @click="clearAllProbes"
            >Clear All</v-btn
          >
        </div>
      </div>
      <div v-if="list_all_the_probe_ip_ct.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold blue--text text--darken-2 mr-2"
            >CT</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_ct" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_ct"
            :key="'ct-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="blue"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
      <div v-if="list_all_the_probe_ip_cu.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold light-blue--text text--darken-2 mr-2"
            >CU</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_cu" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_cu"
            :key="'cu-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="light-blue"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
      <div v-if="list_all_the_probe_ip_cm.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold cyan--text text--darken-2 mr-2"
            >CM</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_cm" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_cm"
            :key="'cm-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="cyan"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
      <div v-if="list_all_the_probe_ip_vn.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold indigo--text text--darken-1 mr-2"
            >VN</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_vn" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_vn"
            :key="'vn-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="indigo"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
      <div v-if="list_all_the_probe_ip_indo.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold teal--text text--darken-1 mr-2"
            >INDO</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_indo" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_indo"
            :key="'indo-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="teal"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
      <div v-if="list_all_the_probe_ip_malaysia.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold green--text text--darken-1 mr-2"
            >Malaysia</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_malaysia" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_malaysia"
            :key="'my-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="green"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
      <div v-if="list_all_the_probe_ip_cambodia.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold amber--text text--darken-2 mr-2"
            >Cambodia</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_cambodia" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_cambodia"
            :key="'kh-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="amber darken-1"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
      <div v-if="list_all_the_probe_ip_th.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold orange--text text--darken-2 mr-2"
            >TH</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_th" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_th"
            :key="'th-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="orange"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
      <div v-if="list_all_the_probe_ip_kr.length" class="mb-3">
        <div class="d-flex align-center mb-1">
          <span
            class="text-caption font-weight-bold purple--text text--darken-1 mr-2"
            >KR</span
          ><v-divider></v-divider>
        </div>
        <v-chip-group multiple v-model="selected_kr" column>
          <v-chip
            v-for="(probe, idx) in list_all_the_probe_ip_kr"
            :key="'kr-' + idx"
            :value="probe.isp + '_' + probe.which_city + '_' + probe.server_ip"
            filter
            outlined
            small
            color="purple"
            >{{ probe.which_city }}_{{ probe.isp }}</v-chip
          >
        </v-chip-group>
      </div>
    </div>

    <!-- <v-row class="ml-2 lime lighten-1">CU</v-row> -->

    <!-- <v-row class="ml-2 yellow lighten-2">CM</v-row> -->

    <div v-if="show_text_field_after_choosing_isp">
      <v-row
        v-if="after_starting_tcping_or_mtr_hide_the_input_row"
        class="mt-3"
      >
        <v-col cols="3" class="ml-2">
          <v-text-field
            label="IP/URL for TCP Trace"
            v-model="ip_or_url_for_tcping"
            @keyup.enter="pass_ip_or_url_to_vuex_store()"
          ></v-text-field>
        </v-col>
        <v-col cols="1">
          <v-text-field
            label="Port"
            v-model="port_for_tcping"
            @keyup.enter="pass_ip_or_url_to_vuex_store()"
          ></v-text-field>
        </v-col>
        <v-col>
          <v-btn
            class="ma-2 text-h4 blue darken-2 white--text"
            @click="pass_ip_or_url_to_vuex_store()"
            >start tcp trace</v-btn
          >
        </v-col>
        <v-col
          >The program will execute this command
          <div class="blue--text text--darken-2 font-weight-black">
            tcptraceroute -n {{ ip_or_url_for_tcping }} {{ port_for_tcping }}
          </div>
        </v-col>
      </v-row>
    </div>
    <v-progress-circular
      class="mb-5"
      v-if="is_any_probe_polling"
      indeterminate
      color="primary"
    ></v-progress-circular>
    <v-row>
      <v-col
        v-for="(elements, index) in list_ct_probe_ip"
        :key="index"
        cols="6"
      >
        <v-card>
          <tcp_trace_for_each_probe
            :probe_ip="elements.server_ip"
            :probe_id="elements.id"
            :linux_hostname="elements.which_city"
            :linux_public_ip="elements.linux_public_ip"
            :isp_name="elements.isp"
            @dns-resolution-status="handle_dns_status"
            @polling-status="handle_polling_status"
            @public-ip-updated="handle_public_ip_updated"
          ></tcp_trace_for_each_probe>
        </v-card>
      </v-col>
    </v-row>

    <!-- <left_side_bar></left_side_bar> -->
  </div>
</template>

<script>
import axios from "axios";
import nav_bar_for_tcping_and_tcp_trace from "@/components/left_and_top_bar/nav_bar_for_tcping_and_tcp_trace.vue";
import tcp_trace_for_each_probe from "@/components/components_within_the_page/tcp_trace_for_each_probe.vue";

export default {
  components: {
    nav_bar_for_tcping_and_tcp_trace,
    tcp_trace_for_each_probe
  },
  methods: {
    handle_dns_status(status) {
      if (!this.dns_probes_tracked.has(status.ip)) {
        this.dns_probes_tracked.add(status.ip);

        if (status.status === "connection_error") {
          this.dns_summary.ssh_failed++;
          this.dns_summary.ssh_failed_probes.push(
            `${status.isp}_${status.hostname}`
          );
        } else {
          this.dns_summary.total++;
          if (status.status === "dns_error") {
            this.dns_summary.dns_poisoned++;
            this.dns_summary.dns_poisoned_probes.push(
              `${status.isp}_${status.hostname}`
            );
          }
        }
      }
    },
    handle_polling_status(status) {
      if (status.polling) {
        this.active_polling_probes.add(status.ip);
      } else {
        this.active_polling_probes.delete(status.ip);
      }
      // Force reactivity update
      this.active_polling_probes = new Set(this.active_polling_probes);
    },
    handle_public_ip_updated(data) {
      const probe = this.list_ct_probe_ip.find(p => p.id === data.probeId);
      if (probe) {
        probe.linux_public_ip = data.newPublicIp;
      }
    },
    async pass_ip_or_url_to_vuex_store() {
      this.error_message = "";
      // Reset DNS summary and polling trackers
      this.dns_summary = {
        total: 0,
        dns_poisoned: 0,
        ssh_failed: 0,
        dns_poisoned_probes: [],
        ssh_failed_probes: []
      };
      this.dns_probes_tracked = new Set();
      this.active_polling_probes = new Set();

      this.hide_the_panel = false;
      this.after_starting_tcping_or_mtr_hide_the_input_row = false;

      // Reset probe results and start batch SSE
      this.$store.commit("resetProbeResults");
      this.$store.commit("setBatchInProgress", true);

      // Get all probe IPs
      const probeIps = this.list_ct_probe_ip.map(p => p.server_ip);

      // Mark all probes as polling
      probeIps.forEach(ip => this.active_polling_probes.add(ip));
      this.active_polling_probes = new Set(this.active_polling_probes);

      try {
        const response = await fetch("/api/sse/batch/mtr", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target: this.ip_or_url_for_tcping,
            port: parseInt(this.port_for_tcping),
            count: 10,
            probes: probeIps
          })
        });

        // Check if response is OK before reading stream
        if (!response.ok) {
          this.error_message = `Server returned ${response.status} ${response.statusText}: ${(await response.text()).slice(0, 300)}`;
          return;
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
          buffer = lines.pop(); // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const json = JSON.parse(line.slice(6));
                if (json.heartbeat) continue; // Skip heartbeat messages
                if (json.all_complete) break readLoop; // All probes completed


                this.$store.commit("updateProbeResult", {
                  probe_ip: json.probe_ip,
                  data: json.data,
                  complete: json.complete
                });

                if (json.complete) {
                  this.active_polling_probes.delete(json.probe_ip);
                  this.active_polling_probes = new Set(
                    this.active_polling_probes
                  );
                }
              } catch (e) {
                console.log("Failed to parse SSE data:", line, e);
              }
            }
          }
        }
      } catch (error) {
        console.error("Batch SSE error:", error);
        this.error_message = `Batch request failed: ${error.message}`;
      } finally {
        this.$store.commit("setBatchInProgress", false);
        this.active_polling_probes = new Set();
        this.after_starting_tcping_or_mtr_hide_the_input_row = true;
      }
    },
    async get_all_the_probes() {
      this.error_message = "";
      this.current_isp = "ALL";
      this.hide_the_panel = true;
      this.show_text_field_after_choosing_isp = true;
      this.list_ct_probe_ip = [];
      this.$store.state.vuex_all_the_probes_that_is_selected = [];
      this.selected_ct = [];
      this.selected_cu = [];
      this.selected_cm = [];
      this.selected_vn = [];
      this.selected_indo = [];
      this.selected_malaysia = [];
      this.selected_cambodia = [];
      this.selected_th = [];
      this.selected_kr = [];
      this.list_all_the_probe_ip_ct = [];
      this.list_all_the_probe_ip_cu = [];
      this.list_all_the_probe_ip_cm = [];
      this.list_all_the_probe_ip_vn = [];
      this.list_all_the_probe_ip_indo = [];
      this.list_all_the_probe_ip_malaysia = [];
      this.list_all_the_probe_ip_cambodia = [];
      this.list_all_the_probe_ip_th = [];
      this.list_all_the_probe_ip_kr = [];

      const isps = [
        "CT",
        "CU",
        "CM",
        "VN",
        "INDO",
        "Malaysia",
        "Cambodia",
        "TH",
        "KR"
      ];
      const requests = isps.map(isp =>
        axios.get(
          `/api/axios_show_which_host_isp_for_webpaping/${isp}`
        )
      );

      try {
        const responses = await Promise.all(requests);
        const sortByCity = arr =>
          arr.sort(
            (a, b) =>
              (a.which_city || "").localeCompare(b.which_city || "") ||
              (a.isp || "").localeCompare(b.isp || "")
          );
        [
          this.list_all_the_probe_ip_ct,
          this.list_all_the_probe_ip_cu,
          this.list_all_the_probe_ip_cm,
          this.list_all_the_probe_ip_vn,
          this.list_all_the_probe_ip_indo,
          this.list_all_the_probe_ip_malaysia,
          this.list_all_the_probe_ip_cambodia,
          this.list_all_the_probe_ip_th,
          this.list_all_the_probe_ip_kr
        ] = responses.map(r => sortByCity(r.data || []));
      } catch (error) {
        console.log(error);
        this.error_message = `Failed to load probes: ${error.message}`;
      }
    },
    async get_ct_probe_ip(which_isp) {
      this.error_message = "";
      this.current_isp = which_isp;
      this.hide_the_panel = false;
      this.show_text_field_after_choosing_isp = true;
      this.list_all_the_probe_ip_ct = [];
      this.list_all_the_probe_ip_cu = [];
      this.list_all_the_probe_ip_cm = [];
      try {
        const response = await axios.get(
          `/api/axios_show_which_host_isp_for_webpaping/${which_isp}`
        );
        this.list_ct_probe_ip = response.data;
        if (!response.data || response.data.length === 0) {
          this.error_message = `No probes are configured for ${which_isp}`;
        }

        // Auto-update missing public IPs for local probes
        const probesWithMissingIp = this.list_ct_probe_ip.filter(
          p => p.id && !p.linux_public_ip
        );

        if (probesWithMissingIp.length > 0) {
          console.log(
            `Found ${probesWithMissingIp.length} probes with missing public IP, auto-updating...`
          );
          for (const probe of probesWithMissingIp) {
            try {
              const updateResponse = await axios.post(
                `/api/update_probe_public_ip/${probe.id}`
              );
              if (updateResponse.data.success) {
                const probeToUpdate = this.list_ct_probe_ip.find(
                  p => p.id === probe.id
                );
                if (probeToUpdate) {
                  probeToUpdate.linux_public_ip = updateResponse.data.public_ip;
                }
                console.log(
                  `Updated public IP for ${probe.which_city}: ${updateResponse.data.public_ip}`
                );
              }
            } catch (err) {
              console.error(
                `Failed to update public IP for probe ${probe.id}:`,
                err
              );
            }
          }
        }
      } catch (error) {
        console.log(error);
        this.error_message = `Failed to load probes: ${error.message}`;
      }
    },
    selectAllProbes() {
      this.selected_ct = this.list_all_the_probe_ip_ct.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
      this.selected_cu = this.list_all_the_probe_ip_cu.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
      this.selected_cm = this.list_all_the_probe_ip_cm.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
      this.selected_vn = this.list_all_the_probe_ip_vn.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
      this.selected_indo = this.list_all_the_probe_ip_indo.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
      this.selected_malaysia = this.list_all_the_probe_ip_malaysia.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
      this.selected_cambodia = this.list_all_the_probe_ip_cambodia.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
      this.selected_th = this.list_all_the_probe_ip_th.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
      this.selected_kr = this.list_all_the_probe_ip_kr.map(
        p => p.isp + "_" + p.which_city + "_" + p.server_ip
      );
    },
    clearAllProbes() {
      this.selected_ct = [];
      this.selected_cu = [];
      this.selected_cm = [];
      this.selected_vn = [];
      this.selected_indo = [];
      this.selected_malaysia = [];
      this.selected_cambodia = [];
      this.selected_th = [];
      this.selected_kr = [];
      this.$store.state.vuex_all_the_probes_that_is_selected = [];
    },
    syncSelectionsToVuex() {
      const allSelected = [
        ...this.selected_ct,
        ...this.selected_cu,
        ...this.selected_cm,
        ...this.selected_vn,
        ...this.selected_indo,
        ...this.selected_malaysia,
        ...this.selected_cambodia,
        ...this.selected_th,
        ...this.selected_kr
      ];
      this.$store.state.vuex_all_the_probes_that_is_selected = allSelected;
    }
  },
  data() {
    return {
      error_message: "",
      ip_or_url_for_tcping: "www.example.com",
      port_for_tcping: "443",
      list_ct_probe_ip: [],
      after_starting_tcping_or_mtr_hide_the_input_row: true,
      show_text_field_after_choosing_isp: false,
      list_all_the_probe_ip_ct: [],
      list_all_the_probe_ip_cu: [],
      list_all_the_probe_ip_cm: [],
      list_all_the_probe_ip_vn: [],
      list_all_the_probe_ip_indo: [],
      list_all_the_probe_ip_malaysia: [],
      list_all_the_probe_ip_cambodia: [],
      list_all_the_probe_ip_th: [],
      list_all_the_probe_ip_kr: [],
      selected_ct: [],
      selected_cu: [],
      selected_cm: [],
      selected_vn: [],
      selected_indo: [],
      selected_malaysia: [],
      selected_cambodia: [],
      selected_th: [],
      selected_kr: [],
      panel: [],
      hide_the_panel: false,
      current_isp: "",
      dns_summary: {
        total: 0,
        dns_poisoned: 0,
        ssh_failed: 0,
        dns_poisoned_probes: [],
        ssh_failed_probes: []
      },
      dns_probes_tracked: new Set(),
      active_polling_probes: new Set()
    };
  },
  created() {
  },
  computed: {
    vuex_all_the_probes_that_is_selected() {
      return this.$store.state.vuex_all_the_probes_that_is_selected;
    },
    is_any_probe_polling() {
      return this.active_polling_probes.size > 0;
    }
  },
  watch: {
    selected_ct: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    selected_cu: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    selected_cm: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    selected_vn: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    selected_indo: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    selected_malaysia: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    selected_cambodia: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    selected_th: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    selected_kr: {
      handler() {
        this.syncSelectionsToVuex();
      },
      deep: true
    },
    vuex_all_the_probes_that_is_selected() {
      console.log("in watch / landing_page_tcp_trace.vue");
      this.list_ct_probe_ip = [];
      if (this.vuex_all_the_probes_that_is_selected.length === 0) return;
      // Build lookup from all loaded probe lists
      const allProbes = [
        ...this.list_all_the_probe_ip_ct,
        ...this.list_all_the_probe_ip_cu,
        ...this.list_all_the_probe_ip_cm,
        ...this.list_all_the_probe_ip_vn,
        ...this.list_all_the_probe_ip_indo,
        ...this.list_all_the_probe_ip_malaysia,
        ...this.list_all_the_probe_ip_cambodia,
        ...this.list_all_the_probe_ip_th,
        ...this.list_all_the_probe_ip_kr
      ];
      const probeMap = {};
      allProbes.forEach(p => {
        probeMap[p.isp + "_" + p.which_city + "_" + p.server_ip] = p;
      });
      this.list_ct_probe_ip = this.vuex_all_the_probes_that_is_selected
        .map(chipValue => probeMap[chipValue])
        .filter(p => p !== undefined);
    },
  }
};
</script>
