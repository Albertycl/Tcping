<template>
  <div>
    <landing_page_customized></landing_page_customized>
  </div>
</template>

<script>
// @ is an alias to /src
import landing_page_customized from "@/components/landing_page/tcping/landing_page_customized.vue";

export default {
  name: "Home",
  components: {
    landing_page_customized,
  },
};
</script>
