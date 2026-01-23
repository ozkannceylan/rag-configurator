// Initialize RAG Configurator database and collections

db = db.getSiblingDB('rag_configurator');

// Create collections with schema validation
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['email', 'password_hash', 'name', 'created_at'],
      properties: {
        email: { bsonType: 'string' },
        password_hash: { bsonType: 'string' },
        name: { bsonType: 'string' },
        created_at: { bsonType: 'date' },
        updated_at: { bsonType: 'date' },
        is_active: { bsonType: 'bool' }
      }
    }
  }
});

db.createCollection('configs');
db.createCollection('documents');
db.createCollection('chunks');
db.createCollection('graph_nodes');
db.createCollection('graph_edges');
db.createCollection('conversations');
db.createCollection('ingestion_jobs');

// Create indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.configs.createIndex({ created_by: 1 });
db.configs.createIndex({ status: 1 });
db.configs.createIndex({ created_at: -1 });
db.documents.createIndex({ config_id: 1 });
db.chunks.createIndex({ config_id: 1 });
db.chunks.createIndex({ document_id: 1 });
db.graph_nodes.createIndex({ config_id: 1, node_type: 1 });
db.graph_nodes.createIndex({ config_id: 1, name: 1 });
db.graph_edges.createIndex({ config_id: 1, source_node: 1 });
db.graph_edges.createIndex({ config_id: 1, target_node: 1 });
db.graph_edges.createIndex({ config_id: 1, relation_type: 1 });
db.conversations.createIndex({ config_id: 1, user_id: 1 });
db.ingestion_jobs.createIndex({ config_id: 1 });

print('RAG Configurator database initialized successfully');
