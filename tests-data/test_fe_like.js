#!/usr/bin/env node

/**
 * Frontend-like chunked upload test using Node.js fetch API
 *
 * This simulates how a real frontend (React, Vue, Angular) would:
 * 1. Create a FormData with data + files
 * 2. Convert to multipart/form-data
 * 3. Send chunks sequentially via fetch API
 */

const fs = require("fs");
const path = require("path");

// Mock FormData and fetch (in real Node.js we'd use node-fetch or built-in fetch)
// For this, we'll use a simple multipart builder

const Configuration = {
  BASE_URL: "http://localhost:8000/api",
  TEST_ID: 2,
  ACCESS_TOKEN:
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY3NDk2OTkxLCJpYXQiOjE3Njc0OTUxOTEsImp0aSI6IjFiZTA4MThkNGYwZjQ4Nzk5ZWJiOWVmNTg0NGVjNDUxIiwidXNlcl9pZCI6IjEwMjQiLCJyb2xlIjoiVCJ9.UQaaG6MAGkRVnX4KkSrzOb0TfXFuYQJNoFz_NxxyCXE",
  CHUNK_SIZE: 512, // 512 bytes chunks - for testing multiple chunks
};

class MultipartFormDataBuilder {
  constructor() {
    this.boundary = `----WebKitFormBoundary${Math.random()
      .toString(16)
      .substr(2, 16)}`;
    this.parts = [];
  }

  addField(name, value) {
    /**
     * Frontend approach: using FormData API
     * formData.append('data', JSON.stringify(...))
     */
    this.parts.push({
      type: "field",
      name,
      value,
    });
  }

  addFile(fieldName, filename, fileData) {
    /**
     * Frontend approach: using FormData API
     * formData.append('chunk_data', fileInputElement.files[0], 'image.png')
     */
    this.parts.push({
      type: "file",
      name: fieldName,
      filename,
      data: fileData,
    });
  }

  build() {
    let payload = Buffer.alloc(0);

    // Process each part (like FormData does)
    for (let i = 0; i < this.parts.length; i++) {
      const part = this.parts[i];

      // Write boundary
      payload = Buffer.concat([
        payload,
        Buffer.from(`--${this.boundary}\r\n`, "utf-8"),
      ]);

      if (part.type === "field") {
        // JSON field
        payload = Buffer.concat([
          payload,
          Buffer.from(
            `Content-Disposition: form-data; name="${part.name}"\r\n`,
            "utf-8"
          ),
          Buffer.from("Content-Type: application/json\r\n\r\n", "utf-8"),
          Buffer.from(
            typeof part.value === "string"
              ? part.value
              : JSON.stringify(part.value),
            "utf-8"
          ),
          Buffer.from("\r\n", "utf-8"),
        ]);
      } else if (part.type === "file") {
        // File field
        payload = Buffer.concat([
          payload,
          Buffer.from(
            `Content-Disposition: form-data; name="${part.name}"; filename="${part.filename}"\r\n`,
            "utf-8"
          ),
          Buffer.from(
            "Content-Type: application/octet-stream\r\n\r\n",
            "utf-8"
          ),
          part.data,
          Buffer.from("\r\n", "utf-8"),
        ]);
      }
    }

    // Write final boundary
    payload = Buffer.concat([
      payload,
      Buffer.from(`--${this.boundary}--\r\n`, "utf-8"),
    ]);

    return payload;
  }
}

function createSamplePng() {
  // Minimal valid PNG (1x1 pixel)
  return Buffer.from([
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1f, 0x15, 0xc4, 0x89, 0x00, 0x00, 0x00,
    0x0a, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9c, 0x63, 0xf8, 0x0f, 0x00, 0x00,
    0x01, 0x01, 0x00, 0xfb, 0xb5, 0xee, 0x36, 0xb8, 0x00, 0x00, 0x00, 0x00,
    0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
  ]);
}

function createTestPayload() {
  console.log("📦 Creating multipart payload (like FormData in frontend)...\n");

  // This is what a frontend would do:
  // const formData = new FormData();
  // formData.append('data', JSON.stringify(testData));
  // formData.append('chunk_data', imageFile1, 'question_1.png');
  // formData.append('chunk_data', imageFile2, 'answer_1a.png');

  const testData = {
    parts: [
      {
        order: 1,
        format: "F",
        description: "Part 1: Reading Comprehension",
        content:
          "<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>",
        questions: [
          {
            question_number: 1,
            content: "What is the main topic of this passage?",
            explanation: "The main topic is about Lorem ipsum text.",
            score: 10,
            resources: { image: "question_1.png" },
            answers: [
              {
                option_label: "A",
                answer_text: "Lorem ipsum",
                is_correct: true,
                resources: { image: "answer_1a.png" },
              },
              {
                option_label: "B",
                answer_text: "Other option",
                is_correct: false,
                resources: {},
              },
            ],
          },
        ],
      },
    ],
  };

  const builder = new MultipartFormDataBuilder();
  builder.addField("data", testData);
  builder.addFile("question_1.png", "question_1.png", createSamplePng());
  builder.addFile("answer_1a.png", "answer_1a.png", createSamplePng());

  const payload = builder.build();

  console.log(`✅ Payload created:`);
  console.log(`   Size: ${payload.length} bytes`);
  console.log(`   Boundary: ${builder.boundary}`);
  console.log(
    `   Content type: multipart/form-data; boundary=${builder.boundary}\n`
  );

  return payload;
}

function divideIntoChunks(payload, chunkSize) {
  console.log(`📚 Dividing payload into chunks...\n`);

  const chunks = [];
  for (let i = 0; i < payload.length; i += chunkSize) {
    chunks.push(payload.slice(i, i + chunkSize));
  }

  console.log(`✅ Divided into ${chunks.length} chunks:`);
  chunks.forEach((chunk, i) => {
    console.log(`   Chunk ${i + 1}: ${chunk.length} bytes`);
  });
  console.log();

  return chunks;
}

async function uploadChunk(
  uploadId,
  chunkNumber,
  totalChunks,
  chunkData,
  isComplete
) {
  /**
   * Frontend would do something like:
   *
   * const response = await fetch('/api/tests/receptive/2', {
   *   method: 'POST',
   *   headers: {
   *     'X-Upload-ID': uploadId,
   *     'X-Chunk-Number': chunkNumber,
   *     'X-Total-Chunks': totalChunks,
   *     'X-Is-Complete': isComplete ? 'true' : 'false',
   *     'Content-Type': 'application/octet-stream',
   *     'Authorization': `Bearer ${token}`,
   *   },
   *   body: chunkData,
   * });
   */

  const url = `${Configuration.BASE_URL}/tests/receptive/${Configuration.TEST_ID}`;

  const headers = {
    "X-Upload-ID": uploadId,
    "X-Chunk-Number": chunkNumber.toString(),
    "X-Total-Chunks": totalChunks.toString(),
    "X-Is-Complete": isComplete ? "true" : "false",
    "Content-Type": "application/octet-stream",
  };

  if (Configuration.ACCESS_TOKEN) {
    headers["Authorization"] = `Bearer ${Configuration.ACCESS_TOKEN}`;
  }

  process.stdout.write(`   Uploading... `);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: chunkData,
    });

    const responseData = await response.json();

    if (response.ok || response.status === 202 || response.status === 201) {
      console.log(`✅ Status: ${response.status}`);
      return { success: true, data: responseData, status: response.status };
    } else {
      console.log(`❌ Status: ${response.status}`);
      console.log(`   Error: ${JSON.stringify(responseData)}`);
      return { success: false, data: responseData, status: response.status };
    }
  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
    return { success: false, error: error.message };
  }
}

async function testFrontendUpload() {
  console.log("═".repeat(70));
  console.log("Frontend-like Chunked Upload Test");
  console.log("═".repeat(70));
  console.log();

  // Step 1: Create payload
  const payload = createTestPayload();

  // Step 2: Divide into chunks
  const chunks = divideIntoChunks(payload, Configuration.CHUNK_SIZE);

  // Step 3: Upload chunks
  console.log("⬆️  Uploading chunks...\n");
  const uploadId = `fe_${Math.random().toString(16).substr(2, 8)}`;
  console.log(`Upload ID: ${uploadId}\n`);

  let allSuccess = true;
  const totalChunks = chunks.length;

  for (let i = 0; i < chunks.length; i++) {
    const chunkNumber = i + 1;
    const isComplete = i === chunks.length - 1;

    process.stdout.write(
      `[Chunk ${chunkNumber}/${totalChunks}] (${chunks[i].length} bytes) `
    );

    const result = await uploadChunk(
      uploadId,
      chunkNumber,
      totalChunks,
      chunks[i],
      isComplete
    );

    if (!result.success) {
      allSuccess = false;
      if (result.data) {
        console.log(`   Response: ${JSON.stringify(result.data, null, 2)}`);
      }
    } else {
      console.log(`   Response: ${JSON.stringify(result.data, null, 2)}`);
    }

    console.log();

    // Small delay between requests
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  console.log("═".repeat(70));
  if (allSuccess) {
    console.log("✅ TEST PASSED - Frontend upload simulation successful!");
  } else {
    console.log("❌ TEST FAILED");
  }
  console.log("═".repeat(70));
}

// Run test
testFrontendUpload().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
