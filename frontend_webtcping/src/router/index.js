import Vue from "vue";
import VueRouter from "vue-router";

// Lazy load routes for better initial bundle size
const landing_page_tcping = () => import("../views/landing_page_tcping.vue");
const landing_page_tcp_trace = () => import("../views/landing_page_tcp_trace.vue");
const landing_page_dig = () => import("../views/landing_page_dig.vue");
const landing_page_curl = () => import("../views/landing_page_curl.vue");
const landing_page_http_ping = () => import("../views/landing_page_http_ping.vue");
const landing_page_customized = () => import("../views/landing_page_customized.vue");
const landing_page_whitelist = () => import("../views/landing_page_whitelist.vue");
const landing_page_all_in_one = () => import("../views/landing_page_all_in_one.vue");
const thailand_test = () => import("../views/thailand_test.vue");

Vue.use(VueRouter);

const routes = [
  {
    path: "/",
    name: "landing_page_tcping",
    component: landing_page_tcping,
    meta: {
      title: "TCPING",
    },
  },
  {
    path: "/tcp_trace",
    name: "landing_page_tcp_trace",
    component: landing_page_tcp_trace,
    meta: {
      title: "TCP_TRACE",
    },
  },
  {
    path: "/dig",
    name: "landing_page_dig",
    component: landing_page_dig,
    meta: {
      title: "DIG",
    },
  },
  {
    path: "/curl",
    name: "landing_page_curl",
    component: landing_page_curl,
    meta: {
      title: "CURL",
    },
  },
  {
    path: "/httping",
    name: "landing_page_http_ping",
    component: landing_page_http_ping,
    meta: {
      title: "HTTPING",
    },
  },
  {
    path: "/customized",
    name: "landing_page_customized",
    component: landing_page_customized,
    meta: {
      title: "CUSTOMIZED",
    },
  },
  {
    path: "/whitelist",
    name: "landing_page_whitelist",
    component: landing_page_whitelist,
    meta: {
      title: "WHITELIST",
    },
  },
  {
    path: "/all-in-one",
    name: "landing_page_all_in_one",
    component: landing_page_all_in_one,
    meta: {
      title: "ALL-IN-ONE",
    },
  },
  {
    path: "/thailand-test",
    name: "thailand_test",
    component: thailand_test,
    meta: {
      title: "Thailand_Test",
    },
  },

];

const router = new VueRouter({
  mode: "history",
  base: process.env.BASE_URL,
  routes,
});

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = to.meta.title;
  }
  next();
});

export default router;
