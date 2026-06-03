import axios from 'axios';

const SRS_API = 'http://localhost:1985';

export function getSrsClient() {
  return {
    listStreams: async () => {
      const { data } = await axios.get(`${SRS_API}/api/v1/streams/`);
      return data.streams || [];
    },

    getStream: async (streamName: string) => {
      const { data } = await axios.get(`${SRS_API}/api/v1/streams/${streamName}`);
      return data;
    },

    closeStream: async (streamName: string) => {
      const { data } = await axios.delete(`${SRS_API}/api/v1/clients/${streamName}`);
      return data;
    },

    getVersion: async () => {
      const { data } = await axios.get(`${SRS_API}/api/v1/versions`);
      return data;
    },
  };
}
