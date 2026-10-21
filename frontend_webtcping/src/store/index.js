import Vue from "vue";
import Vuex from "vuex";

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    vuex_ip_or_url_for_tcping: "from_vuex_default_url",
    vuex_port_for_tcping: "from_vuex_default_port",
    vuex_ip_for_hostfile: "",
    vuex_url_for_hostfile: "",
    vuex_tls_12_or_tls13: "",
    vuex_all_the_probes_that_is_selected: [],
    // Batch SSE probe results
    probeResults: {}, // { "192.0.2.12": "result..." }
    probeCompleted: {}, // { "192.0.2.12": true, ... }
    batchInProgress: false,
    // Separate state for ALL-IN-ONE page to avoid collision
    tcpingProbeResults: {},
    tcpingProbeCompleted: {},
    tcpingBatchInProgress: false,
    mtrProbeResults: {},
    mtrProbeCompleted: {},
    mtrBatchInProgress: false
  },
  mutations: {
    passing_in_the_payload(state, payload_object) {
      console.log("in mutations for passing_in_the_payload");
      state.vuex_ip_or_url_for_tcping = payload_object.key_ip_or_url_for_tcping;
      // console.log(`payload_object=${payload_object}`)
      state.vuex_port_for_tcping = payload_object.key_port_for_tcping;
      state.vuex_ip_for_hostfile = payload_object.key_ip_for_the_hostfile;
      state.vuex_url_for_hostfile = payload_object.key_url_for_the_hostfile;
      state.vuex_tls_12_or_tls13 = payload_object.key_tls_12_or_tls13;
    },
    add_to_probes_list(state, payload_object) {
      console.log("add / in store index.js");
      state.vuex_all_the_probes_that_is_selected.push(payload_object);
    },
    remove_from_probes_list(state, payload_object) {
      console.log("remove / in store index.js");
      state.vuex_all_the_probes_that_is_selected = state.vuex_all_the_probes_that_is_selected.filter(
        item => item !== payload_object
      );
    },
    // Batch SSE mutations
    updateProbeResult(state, { probe_ip, data, complete }) {
      Vue.set(state.probeResults, probe_ip, data);
      if (complete) {
        Vue.set(state.probeCompleted, probe_ip, true);
      }
    },
    resetProbeResults(state) {
      state.probeResults = {};
      state.probeCompleted = {};
    },
    setBatchInProgress(state, value) {
      state.batchInProgress = value;
    },
    // Mutations for ALL-IN-ONE page - TCPING
    updateTcpingProbeResult(state, { probe_ip, data, complete }) {
      Vue.set(state.tcpingProbeResults, probe_ip, data);
      if (complete) {
        Vue.set(state.tcpingProbeCompleted, probe_ip, true);
      }
    },
    resetTcpingProbeResults(state) {
      state.tcpingProbeResults = {};
      state.tcpingProbeCompleted = {};
    },
    setTcpingBatchInProgress(state, value) {
      state.tcpingBatchInProgress = value;
    },
    // Mutations for ALL-IN-ONE page - MTR
    updateMtrProbeResult(state, { probe_ip, data, complete }) {
      Vue.set(state.mtrProbeResults, probe_ip, data);
      if (complete) {
        Vue.set(state.mtrProbeCompleted, probe_ip, true);
      }
    },
    resetMtrProbeResults(state) {
      state.mtrProbeResults = {};
      state.mtrProbeCompleted = {};
    },
    setMtrBatchInProgress(state, value) {
      state.mtrBatchInProgress = value;
    }
  },
  actions: {},
  modules: {}
});
