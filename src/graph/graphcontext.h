#ifndef _GRAPHCONTEXT_H
#define _GRAPHCONTEXT_H

#include <assert.h>
#include "../redismodule.h"
#include "../index/index.h"
#include "../stores/store.h"

// graph.h defines
#define GRAPH_DEFAULT_NODE_CAP 16384    // Default number of nodes a graph can hold before resizing.
#define GRAPH_DEFAULT_RELATION_CAP 16   // Default number of different relationships a graph can hold before resizing.
#define GRAPH_DEFAULT_LABEL_CAP 16      // Default number of different labels a graph can hold before resizing.
#define GRAPH_NO_LABEL -1               // Labels are numbered [0-N], -1 represents no label.
#define GRAPH_NO_RELATION -1            // Relations are numbered [0-N], -1 represents no relation.

// This would really belong in store.h, but I'm putting it here momentarily for visiility
typedef struct {
  LabelStore *store;
  char *storename;
  LabelStoreType type;
} StoreHandle;

typedef struct {
  RedisModuleCtx *ctx;
  char *graph_name;

  // We could possibly move Graph's label and relation cap and count variables
  // here as well
  char **relation_labels;
  char **node_labels;

  // TODO dups of Graph members; should belong exclusively to one
  size_t relation_cap;            // Number of relations graph can hold.
  size_t relation_count;          // Number of relation matrices.
  size_t node_cap;               // Number of labels graph can hold.
  size_t node_count;             // Number of label matrices.

  Index **indices;
  int index_count;

  LabelStore *edge_allstore;
  LabelStore *node_allstore;
  LabelStore **edge_stores;
  LabelStore **node_stores;
  // StoreHandle **edge_stores;
  // StoreHandle **node_stores;
} GraphContext;

void GraphContext_New(RedisModuleCtx *ctx, const char *graph_name);

void GraphContext_Get(RedisModuleCtx *ctx, const char *graph_name);

void GraphContext_AddNode(const char *label);
void GraphContext_AddRelation(const char *label);

const char* GraphContext_GetLabelString(int label_idx, LabelStoreType t);
int GraphContext_GetLabelID(const char *label, LabelStoreType t);

bool GraphContext_HasIndices(void);
Index* GraphContext_GetIndex(const char *label, const char *property);
void GraphContext_AddIndex(Index* idx);

LabelStore* GraphContext_AllStore(LabelStoreType t);
LabelStore* GraphContext_GetStoreByString(const char *label, LabelStoreType t);

void GraphContext_Free();

#endif

