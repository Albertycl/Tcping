<template>
  <v-card>
    <v-card-title>
      Whitelist Management
      <v-spacer></v-spacer>
      <v-btn color="primary" @click="openDialog()">Add Condition</v-btn>
    </v-card-title>
    <v-row>
      <v-col cols="12">
        <h3 class="green--text text--darken-2 mb-2">Success Conditions</h3>
        <v-data-table
          :headers="headers"
          :items="successConditions"
          :loading="loading"
          class="elevation-1 mb-5"
        >
          <template v-slot:item.is_enabled="{ item }">
            <v-simple-checkbox v-model="item.is_enabled" disabled></v-simple-checkbox>
          </template>
          <template v-slot:item.actions="{ item }">
            <v-icon small class="mr-2" @click="openDialog(item)">mdi-pencil</v-icon>
            <v-icon small @click="deleteItem(item)">mdi-delete</v-icon>
          </template>
        </v-data-table>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <h3 class="red--text text--darken-2 mb-2">Failure Conditions</h3>
        <v-data-table
          :headers="headers"
          :items="failureConditions"
          :loading="loading"
          class="elevation-1"
        >
          <template v-slot:item.is_enabled="{ item }">
            <v-simple-checkbox v-model="item.is_enabled" disabled></v-simple-checkbox>
          </template>
          <template v-slot:item.actions="{ item }">
            <v-icon small class="mr-2" @click="openDialog(item)">mdi-pencil</v-icon>
            <v-icon small @click="deleteItem(item)">mdi-delete</v-icon>
          </template>
        </v-data-table>
      </v-col>
    </v-row>

    <v-dialog v-model="dialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ formTitle }}</span>
        </v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12">
                <v-text-field v-model="editedItem.condition_name" label="Name"></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-text-field v-model="editedItem.condition_pattern" label="Pattern (Regex or String)"></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-select
                  v-model="editedItem.condition_type"
                  :items="['success', 'failure']"
                  label="Type"
                ></v-select>
              </v-col>
              <v-col cols="12">
                <v-text-field v-model="editedItem.country_specific" label="Country (Optional, e.g. VN)"></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-text-field v-model="editedItem.description" label="Description"></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-checkbox v-model="editedItem.is_enabled" label="Enabled"></v-checkbox>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue darken-1" text @click="close">Cancel</v-btn>
          <v-btn color="blue darken-1" text @click="save">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script>
import axios from "axios";

export default {
  data: () => ({
    dialog: false,
    loading: false,
    headers: [
      { text: "Name", value: "condition_name" },
      { text: "Pattern", value: "condition_pattern" },
      { text: "Type", value: "condition_type" },
      { text: "Country", value: "country_specific" },
      { text: "Enabled", value: "is_enabled" },
      { text: "Actions", value: "actions", sortable: false },
    ],
    conditions: [],
    editedIndex: -1,
    editedItem: {
      condition_name: "",
      condition_pattern: "",
      condition_type: "success",
      country_specific: "",
      description: "",
      is_enabled: true,
    },
    defaultItem: {
      condition_name: "",
      condition_pattern: "",
      condition_type: "success",
      country_specific: "",
      description: "",
      is_enabled: true,
    },
    apiBaseUrl: "/api/api/whitelist", // Adjust if needed
  }),

  computed: {
    formTitle() {
      return this.editedIndex === -1 ? "New Condition" : "Edit Condition";
    },
    successConditions() {
      return this.conditions.filter((c) => c.condition_type === "success");
    },
    failureConditions() {
      return this.conditions.filter((c) => c.condition_type === "failure");
    },
  },

  created() {
    this.initialize();
  },

  methods: {
    initialize() {
      this.loading = true;
      axios
        .get(this.apiBaseUrl)
        .then((response) => {
          this.conditions = response.data;
        })
        .catch((error) => {
          console.error("Error fetching whitelist:", error);
        })
        .finally(() => {
          this.loading = false;
        });
    },

    openDialog(item) {
      if (item) {
        this.editedIndex = this.conditions.indexOf(item);
        this.editedItem = Object.assign({}, item);
      } else {
        this.editedIndex = -1;
        this.editedItem = Object.assign({}, this.defaultItem);
      }
      this.dialog = true;
    },

    close() {
      this.dialog = false;
      this.$nextTick(() => {
        this.editedItem = Object.assign({}, this.defaultItem);
        this.editedIndex = -1;
      });
    },

    save() {
      if (this.editedIndex > -1) {
        // Update
        axios
          .put(`${this.apiBaseUrl}/${this.editedItem.id}`, this.editedItem)
          .then((response) => {
            Object.assign(this.conditions[this.editedIndex], response.data);
            this.close();
          })
          .catch((error) => {
            console.error("Error updating condition:", error);
          });
      } else {
        // Create
        axios
          .post(this.apiBaseUrl, this.editedItem)
          .then((response) => {
            this.conditions.push(response.data);
            this.close();
          })
          .catch((error) => {
            console.error("Error creating condition:", error);
          });
      }
    },

    deleteItem(item) {
      if (confirm("Are you sure you want to delete this item?")) {
        const index = this.conditions.indexOf(item);
        axios
          .delete(`${this.apiBaseUrl}/${item.id}`)
          .then(() => {
            this.conditions.splice(index, 1);
          })
          .catch((error) => {
            console.error("Error deleting condition:", error);
          });
      }
    },
  },
};
</script>
